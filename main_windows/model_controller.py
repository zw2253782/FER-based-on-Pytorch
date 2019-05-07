# coding=utf-8
import sys
import torch
from torch.autograd import Variable
import numpy as np
from PIL import Image
sys.path.append("..")
from networks.ACCNN import ACCNN
import transforms.transforms as transforms
from utils.face_recognition import crop_face_area_and_get_landmarks, get_img_with_landmarks

IMG_MEAN = [0.449]
IMG_STD = [0.226]
use_cuda = torch.cuda.is_available()
use_cuda = False
DEVICE = torch.device("cuda" if use_cuda else "cpu")


class ModelController():
    '''
    用于系统对于模型的控制，以及使用模型进行表情识别
    '''
    def __init__(self, model_root_pre_path='', dataset='FER2013', tr_using_crop=True, *args, **kwargs):
        self.model_root_pre_path = model_root_pre_path

        self.model = ACCNN(7, pre_trained=True, dataset=dataset, root_pre_path=model_root_pre_path, fold=5, virtualize=True,
                           using_fl=False).to(DEVICE)
        self.model_fl = ACCNN(7, pre_trained=True, dataset=dataset, root_pre_path=model_root_pre_path, fold=5, virtualize=True,
                              using_fl=True).to(DEVICE)
        self.tr_using_crop = tr_using_crop
        if self.tr_using_crop:
            crop_img_size = int(self.model.input_size * 1.2)
            self.transform_test = transforms.Compose([
                transforms.Resize(crop_img_size),
                transforms.TenCrop(self.model.input_size),
                transforms.Lambda(lambda crops: torch.stack(
                    [transforms.Normalize(IMG_MEAN, IMG_STD)(transforms.ToTensor()(crop)) for crop in crops])),
            ])
        else:
            self.transform_test = transforms.Compose([
                transforms.Resize(int(self.model.input_size)),
                transforms.ToTensor(),
                transforms.Normalize(IMG_MEAN, IMG_STD),
            ])

    def fer_recognization(self, img_arr, weights_fl=0.5):
        """
        人脸识别
        :param img_arr: img的numpy array对象
        :param weights_fl: 对于face_landmarks的权重，0~1之间
        :param resize_size:
        :return:
        """
        img = Image.fromarray(img_arr).convert("L")
        img, face_box, face_landmarks = crop_face_area_and_get_landmarks(img)
        landmarks_img = get_img_with_landmarks(img, face_landmarks)
        inputs = self.transform_test(img)
        inputs_fl = self.transform_test(landmarks_img)

        bs = 1
        ncrops = 1
        if self.tr_using_crop:
            ncrops, c, h, w = np.shape(inputs)
        else:
            c, h, w = np.shape(inputs)
        # print(np.shape(inputs))
        with torch.no_grad():
            inputs, inputs_fl = inputs.view(-1, c, h, w), inputs_fl.view(-1, c, h, w)
            if use_cuda:
                inputs, inputs_fl = inputs.to(DEVICE), inputs_fl.to(DEVICE)
            self.clean_model_features_out()
            inputs, inputs_fl = Variable(inputs), Variable(inputs_fl)
            outputs, outputs_fl = self.model(inputs), self.model_fl(inputs_fl)
            if self.tr_using_crop:
                outputs_avg = outputs.view(bs, ncrops, -1).mean(1)  # avg over crops
                outputs_fl_avg = outputs_fl.view(bs, ncrops, -1).mean(1)  # avg over crops
            else:
                outputs_avg = outputs
                outputs_fl_avg = outputs_fl
            real_outputs = (1-weights_fl)*outputs_avg.data+weights_fl*outputs_fl_avg.data
            _, predicted = torch.max(real_outputs, 1)  # 此处 1 表示维度
            # print(predicted)
            softmax_rate = (outputs_avg.data, outputs_fl_avg.data, real_outputs.data)
        return face_box, self.model.output_map[predicted.item()], softmax_rate

    def clean_model_features_out(self):
        """
        清空特征层的输出缓存
        :return: 无
        """
        self.model.clean_features_out()
        self.model_fl.clean_features_out()