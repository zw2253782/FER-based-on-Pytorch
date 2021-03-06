# coding=utf-8
import os
import random
import pickle
import pandas as pd
from PIL import Image
import numpy as np
import torch.utils.data as data
import sys
sys.path.append('..')
from utils.face_recognition import crop_face_area_and_get_landmarks, get_img_with_landmarks

class FER2013(data.Dataset):
    """`FER2013 Dataset.
    Args:
        is_train (bool, optional): If True, creates dataset from training set, otherwise creates from test set.
        private_test (bool, optional): If True, creates test set from PrivateTest, otherwise creates from PublicTest.
        transform (callable, optional): A function/transform that  takes in an PIL image and returns a transformed version.
                                        E.g, ``transforms.RandomCrop``
        target_type(str, optional): Using for target type: "fa" for "float array", "ls" for "long single".
                                    E.g, ``MSELoss will use fa``; ``CrossEntropyLoss will use ls``
        img_dir_pre_path (str, optional): The relative path of the data dictionary and main file.
        using_fl (bool, optional): Whether using face_landmarks to crop original img.

        The dataset contains 28,709 training images, 3,589 validation images and 3,589 test images with seven expression labels (0=anger, 1=disgust, 2=fear, 3=happiness, 4=sadness, 5=surprise and 6=neutral)
        There are anger:4953, disgust:547, fear:5121, happiness:8989, sadness:6077, surprise:4002 and neutral:6198 images in total.
        And the data has been splited into 3 types: Training, PrivateTest(validation), PublicTest(test)
            Training: anger:3995, disgust:436, fear:4097, happiness:7215, sadness:4830, surprise:3171 and neutral:4965
            PrivateTest: anger:491, disgust:55, fear:528, happiness:879, sadness:594, surprise:416 and neutral:626
            PublicTest: anger:467, disgust:56, fear:496, happiness:895, sadness:653, surprise:415 and neutral:607
    """

    def __init__(self, is_train=True, private_test=True, transform=None, target_type="ls",
                 img_dir_pre_path="data/fer2013", using_fl=False):
        name = 'FER2013'
        if is_train:
            name += "_" + 'train'
        else:
            name += "_" + 'test'
        if using_fl:
            name += "_" + "fl"
        if img_dir_pre_path.split("/")[0] == '..':
            self.dump_self_path = '../Saved_DataSets/' + name + '.pickle'
        else:
            self.dump_self_path = 'Saved_DataSets/' + name + '.pickle'

        if os.path.exists(self.dump_self_path):
            self.load()
        else:

            if target_type == "fa":
                self.classes_map = {0: np.array([1., 0., 0., 0., 0., 0., 0.], dtype=float),
                                    1: np.array([0., 1., 0., 0., 0., 0., 0.], dtype=float),
                                    2: np.array([0., 0., 1., 0., 0., 0., 0.], dtype=float),
                                    3: np.array([0., 0., 0., 1., 0., 0., 0.], dtype=float),
                                    4: np.array([0., 0., 0., 0., 1., 0., 0.], dtype=float),
                                    5: np.array([0., 0., 0., 0., 0., 1., 0.], dtype=float),
                                    6: np.array([0., 0., 0., 0., 0., 0., 1.], dtype=float)}
            elif target_type == "ls":
                self.classes_map = {0: 0,
                                    1: 1,
                                    2: 2,
                                    3: 3,
                                    4: 4,
                                    5: 5,
                                    6: 6}
            else:
                assert("target_type should be 'fa' or 'ls', but input is %s" % (target_type))
            self.img_data_file_path = os.path.join(img_dir_pre_path, 'fer2013.csv')
            self.img_no_fl_folder_path = img_dir_pre_path+"_no_fl"
            self.save_img_no_fl = False  # 是否存储未识别出人脸的图片，默认存于 $(img_dir_pre_path)_no_fl 文件夹
            if self.save_img_no_fl:
                if not os.path.exists(self.img_no_fl_folder_path):
                    os.mkdir(self.img_no_fl_folder_path)
            self.transform = transform
            self.is_train = is_train  # train set or test set
            self.private_test = private_test
            self.using_fl = using_fl
            self.name = 'FER2013'

            np_img_data = np.array(pd.read_csv(self.img_data_file_path))
            print("正在处理图片数据...")
            self.train_data = []
            self.train_data_num = 0
            self.train_classes = []
            self.test_data = []
            self.test_data_num = 0
            self.test_classes = []
            # self.cropped_img_path = img_dir_pre_path+"_cropped"
            # self.landmarks_img_path = img_dir_pre_path + "_fl"
            for line in np_img_data:
                if line[2] == 'Training':
                    self.train_data_num += 1
                    if is_train:
                        img_origin = Image.fromarray(np.reshape(np.array(line[1].split(" "), dtype=float), (48, 48)))
                        img, face_box, face_landmarks = crop_face_area_and_get_landmarks(img_origin)
                        if face_box is None or face_landmarks is None:
                            if self.save_img_no_fl:
                                img_origin = img_origin.convert("L")
                                img_origin.save(os.path.join(self.img_no_fl_folder_path, str(self.train_data_num)+"_train.png"))
                            self.train_data_num -= 1
                            continue
                        if using_fl:
                            landmarks_img = get_img_with_landmarks(img, face_landmarks)
                            self.train_data.append(landmarks_img)
                        else:
                            self.train_data.append(img)
                        self.train_classes.append(self.classes_map[line[0]])
                elif private_test and line[2] == 'PrivateTest':
                    self.test_data_num += 1
                    if not is_train:
                        img_origin = Image.fromarray(np.reshape(np.array(line[1].split(" "), dtype=float), (48, 48)))
                        img, face_box, face_landmarks = crop_face_area_and_get_landmarks(img_origin)
                        if face_box is None or face_landmarks is None:
                            if self.save_img_no_fl:
                                img_origin = img_origin.convert("L")
                                img_origin.save(os.path.join(self.img_no_fl_folder_path, str(self.test_data_num )+"_test.png"))
                            self.test_data_num -= 1
                            continue
                        if using_fl:
                            landmarks_img = get_img_with_landmarks(img, face_landmarks)
                            self.test_data.append(landmarks_img)
                        else:
                            self.test_data.append(img)
                        self.test_classes.append(self.classes_map[line[0]])
                elif not private_test and line[2] == 'PublicTest':
                    self.test_data_num += 1
                    if not is_train:
                        img_origin = Image.fromarray(np.reshape(np.array(line[1].split(" "), dtype=float), (48, 48)))
                        img, face_box, face_landmarks = crop_face_area_and_get_landmarks(img_origin)
                        if face_box is None or face_landmarks is None:
                            if self.save_img_no_fl:
                                img_origin = img_origin.convert("L")
                                img_origin.save(os.path.join(self.img_no_fl_folder_path, str(self.test_data_num)+"_test.png"))
                            self.test_data_num -= 1
                            continue
                        if using_fl:
                            landmarks_img = get_img_with_landmarks(img, face_landmarks)
                            self.test_data.append(landmarks_img)
                        else:
                            self.test_data.append(img)
                        self.test_classes.append(self.classes_map[line[0]])
            print("处理图片数据完成！")
            self.save()
        print("train_num: ", self.train_data_num, " test_num:", self.test_data_num)

    def __getitem__(self, index):
        """
        Args:
            index (int): Index

        Returns:
            tuple: (image, target) where target is index of the target class.
        """
        if index >= self.__len__():
            return None, None

        if self.is_train:
            img, cla = self.train_data[index], self.train_classes[index]
        else:
            img, cla = self.test_data[index], self.test_classes[index]

        # 由于存在 random_crop 等的随机处理，应该是读取的时候进行，这样每个epoch都能够获取不同的random处理
        if self.transform is not None:
            img = self.transform(img)
        return img, cla

    def __len__(self):
        """
        Returns:
            int: data num.
        """
        if self.is_train:
            return self.train_data_num
        else:
            return self.test_data_num

    def set_transform(self, transform):
        self.transform = transform

    def save(self):
        print("saving to pickle file: %s" % self.dump_self_path)
        if not os.path.exists('Saved_DataSets'):
            os.mkdir('Saved_DataSets')
        with open(self.dump_self_path, 'wb') as f:
            # Pickle the class using the highest protocol available.
            pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)
        print("saving over!")

    def load(self):
        print("loading from pickle file: %s" % self.dump_self_path)
        with open(self.dump_self_path, 'rb') as f:
            # The protocol version used is detected automatically, so we do not have to specify it.
            temp = pickle.load(f)
        self.classes_map = temp.classes_map
        self.img_data_file_path = temp.img_data_file_path
        self.img_no_fl_folder_path = temp.img_no_fl_folder_path
        self.save_img_no_fl = temp.save_img_no_fl
        self.transform = temp.transform
        self.is_train = temp.is_train
        self.private_test = temp.private_test
        self.using_fl = temp.using_fl
        self.name = temp.name
        self.train_data = temp.train_data
        self.train_data_num = temp.train_data_num
        self.train_classes = temp.train_classes
        self.test_data = temp.test_data
        self.test_data_num = temp.test_data_num
        self.test_classes = temp.test_classes
        print("loading over!")


if __name__ == "__main__":
    f1 = FER2013(is_train=True, img_dir_pre_path="../data/fer2013")
    f2 = FER2013(is_train=False, img_dir_pre_path="../data/fer2013")
    print(f1.__len__(), f2.__len__())

    from utils.utils import draw_img

    draw_img(f1.__getitem__(0)[0])
    draw_img(f2.__getitem__(0)[0])
