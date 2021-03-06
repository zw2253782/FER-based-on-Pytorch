# coding=utf-8
import os
import time
import torch
from PIL import Image
from math import ceil
import torch.nn as nn
import numpy as np
import utils.utils as utils
from transforms.functional import normalize
from main_windows.model_controller import IMG_MEAN, IMG_STD

def draw_features_of_net(net, test_inputs, img_name_pre="", img_save_dir="Saved_Virtualizations"):
    """
    绘制网络所有的特征层的输入和输出情况：给网络添加钩子，并读取中间层的输入和输出，构建 Image 并保存
    :param net: 网络
    :param test_inputs: 测试的输入
    :param img_name_pre: 存储的图片的前缀
    :param img_save_dir: 存储的目录
    :return: None
    """
    # 定义钩子函数
    features_hook = []
    def get_features_hook(self, input, output):
        features_hook.append(input)
        features_hook.append(output)
    # 绑定钩子函数
    handlers = []
    for layer in net.named_modules():
        if isinstance(layer[1], nn.Conv2d):
            handlers.append(layer[1].register_forward_hook(get_features_hook))
    # 测试
    with torch.no_grad():
        net(test_inputs)
    # 删除绑定
    for handler in handlers:
        handler.remove()

    # 可视化展示
    for layer_number in range(len(features_hook)):
        if layer_number % 2 == 0:
            build_and_draw_img_of_features(features_hook[layer_number][0].cpu(), int(layer_number/2), type='in',
                                           img_name_pre=img_name_pre, img_save_dir=img_save_dir)
        else:
            build_and_draw_img_of_features(features_hook[layer_number][0].cpu(), int(layer_number/2), type='out',
                                           img_name_pre=img_name_pre, img_save_dir=img_save_dir)
    build_and_draw_img_of_features(np.array(net.features_out[0].cpu()), -1, type='end',
                                   img_name_pre=img_name_pre, img_save_dir=img_save_dir)


def build_and_draw_img_of_features(images, feature_index, type="", img_name_pre="", img_save_dir="Saved_Virtualizations"):
    """
    构建并绘制特征层的图像
    :param images: 钩子函数获取的特征层，[tuple, tuple, ..., tuple]
    :param feature_index: 特征序号
    :param type: 特征类型('in'表示特征层的输入，'out'表示特征层的输出，'end'表示网络最终特征输出)
    :param img_name_pre: 存储的特征层 img 名称前缀
    :param img_save_dir: 存储的特征层 img 路径
    :return: 保存的img路径
    """
    # print(images.shape)
    img_save_name = img_name_pre + "_feature_layer_" + str(feature_index) + "_" + type
    for i in range(len(images)):
        # print("-----------img %s------------" % str(i))
        image = images[i]
        start_build_time = time.time()
        img = build_img_of_features(image)
        end_build_time = time.time()
        build_duration = round((end_build_time-start_build_time) * 1000, 2)
        print("build_duration:", build_duration)
        if not os.path.exists(img_save_dir):
            os.mkdir(img_save_dir)
        img_save_path = os.path.join(img_save_dir, img_save_name + "_of_img_" + str(i))
        start_draw_time = time.time()
        utils.draw_img(img, img_save_path, plt_show=False)
        end_draw_time = time.time()
        draw_duration = round((end_draw_time-start_draw_time) * 1000, 2)
        print("draw_duration:", draw_duration)
        break
    return img_save_path

def build_img_of_features(image, blank_size=2):
    """
    构建特征层的 Image 对象。image为中间某层的输入或者输出，将这些 image 构建为一个 Image 对象，用于存为一个图片
    :param image: 特征层的输入或者输出
    :param blank_size: 样图之间的间距（pixel）
    :return: 构建好的 Image
    """
    if len(image.shape) == 2:
        image = image.reshape(1, image.shape[0], image.shape[1])
    image_shape = image.shape
    # print(image_shape)
    # print(image)
    # image = normalize(image, IMG_MEAN, IMG_STD)
    # print(image)
    col_num = int(ceil(image_shape[0] ** 0.5))
    row_num = int(ceil(image_shape[0] / col_num))
    height = row_num * image_shape[1]
    width = col_num * image_shape[2]
    # print(col_num, row_num, height, width)
    img_arr = np.array(
        [[0.5 for _ in range(width + (col_num - 1) * blank_size)] for _ in range(height + (row_num - 1) * blank_size)])
    for j in range(len(image)):
        start_row_index = (j // col_num) * (blank_size + image_shape[1])
        start_col_index = (j % col_num) * (blank_size + image_shape[2])
        image_np = image[j].numpy()
        img_arr[start_row_index:start_row_index+image_np.shape[0], start_col_index:start_col_index+image_np.shape[1]] = image_np
        # 上面这句相当于下面这个循环，但是下面的循环相比上面要速度慢很多
        # for row_pixel_index in range(image_shape[1]):
        #     for col_pixel_index in range(image_shape[2]):
        #         img_arr[start_row_index + row_pixel_index][start_col_index + col_pixel_index] = \
        #             image[j][row_pixel_index][col_pixel_index]

    return Image.fromarray(img_arr)


def build_and_draw_bar_img(output_map, y, img_name_pre="", img_save_dir="Saved_Virtualizations",
                           bar_color=(118 / 255, 141 / 255, 50 / 255, 200 / 255)):
    """
    根据x和y进行条形图的绘制
    :param output_map: index对应到类别的map
    :param y: 每个x的具体值
    :param img_name_pre: 存储的条形图的 img 名称前缀
    :param img_save_dir: 存储的目录
    :return: 保存的img路径
    """
    # print(softmax_rate)
    img_save_name = img_name_pre + "_bar_img"
    img_save_path = os.path.join(img_save_dir, img_save_name)
    utils.draw_bar_img(output_map, y, img_save_path, plt_show=False, bar_color=bar_color)
    return img_save_path


def draw_weights_of_net(net, img_name_pre="", blank_size=2, img_save_dir="Saved_Virtualizations"):
    """
    绘制网络所有的特征层的内核参数情况
    :param net: 网络
    :param img_name_pre: 存储的图片的前缀
    :param blank_size: 样图之间的间距（pixel）
    :param img_save_dir: 存储的目录
    :return: None
    """
    layer_number = 0
    stat_dict = net.state_dict()
    for dic in stat_dict.keys():
        dic_splited = dic.split(".")
        if dic_splited[0] == 'features' and dic_splited[2] == 'weight':
            img_save_name = img_name_pre + "_weight_layer_" + str(layer_number)
            weights = stat_dict[dic]
            # print(dic, weights)
            out_channel_num = len(weights)
            in_channel_num = len(weights[0])
            kernel_height = len(weights[0][0])
            kernel_width = len(weights[0][0][0])
            img_arr = np.array([[0.5 for _ in range(kernel_width*in_channel_num+(in_channel_num-1)*blank_size)]for _ in range(kernel_height*out_channel_num+(out_channel_num-1)*blank_size)])
            # print(img_arr.shape)
            for out_channel_number in range(out_channel_num):
                for in_channel_number in range(in_channel_num):
                    start_row_index, start_col_index = (out_channel_number)*(blank_size+kernel_height), (in_channel_number)*(blank_size+kernel_width)
                    kernel = weights[out_channel_number][in_channel_number]
                    # print(kernel.shape)
                    for row_pixel_index in range(kernel.shape[0]):
                        for col_pixel_index in range(kernel.shape[1]):
                            img_arr[start_row_index+row_pixel_index][start_col_index+col_pixel_index] = kernel[row_pixel_index][col_pixel_index]
            img = Image.fromarray(img_arr)
            if not os.path.exists(img_save_dir):
                os.mkdir(img_save_dir)
            utils.draw_img(img, os.path.join(img_save_dir, img_save_name), plt_show=False)
            layer_number += 1


if __name__ == "__main__":
    from torch.autograd import Variable
    import transforms.transforms as transforms
    from networks.ACCNN import ACCNN
    from dal.CKPlus_DataSet import CKPlus
    from dal.FER2013_DataSet import FER2013
    from dal.JAFFE_DataSet import JAFFE

    '''------------------主要在下面这一行设置可视化的参数-----------------'''
    net_name, dataset, fold, fl = 'ACCNN', 'CK+', 5, True  # 当前只用于绘制 ACCNN

    # 配置信息
    enabled_nets = ["ACCNN"]
    enabled_datasets = ["JAFFE", "CK+", "FER2013"]
    use_cuda = torch.cuda.is_available()
    DEVICE = torch.device("cuda" if use_cuda else "cpu")
    target_type, n_classes = 'ls', 7

    print("------------Preparing Model...----------------")
    net = ACCNN(n_classes=n_classes, pre_trained=True, dataset=dataset, fold=fold, virtualize=True, using_fl=fl).to(DEVICE)
    print("------------%s Model Already be Prepared------------" % net_name)
    input_img_size = net.input_size
    IMG_MEAN = [0.449]
    IMG_STD = [0.226]
    transform_train = transforms.Compose([
        transforms.Resize(input_img_size),  # 缩放将图片的最小边缩放为 input_img_size，因此如果输入是非正方形的，那么输出也不是正方形的
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(30),
        transforms.ToTensor(),
        transforms.Normalize(IMG_MEAN, IMG_STD),
    ])
    transform_test = transforms.Compose([
        transforms.Resize(input_img_size),  # 缩放将图片的最小边缩放为 input_img_size，因此如果输入是非正方形的，那么输出也不是正方形的
        transforms.ToTensor(),
        transforms.Normalize(IMG_MEAN, IMG_STD),
    ])
    print("------------Preparing Data...----------------")
    if dataset == "JAFFE":
        test_data = JAFFE(is_train=False, transform=transform_test, target_type=target_type, using_fl=fl)
    elif dataset == "CK+":
        test_data = CKPlus(is_train=False, transform=transform_test, target_type=target_type, using_fl=fl)
    elif dataset == "FER2013":
        test_data = FER2013(is_train=False, private_test=True, transform=transform_test, target_type=target_type,
                            using_fl=fl)
    else:
        assert ("opt.dataset should be in %s, but got %s" % (enabled_datasets, dataset))
    test_loader = torch.utils.data.DataLoader(test_data, batch_size=1, shuffle=True)
    print("------------%s Data Already be Prepared------------" % dataset)
    print("---------------net: %s, dataset: %s---------------" % (net_name, dataset))

    # 获取数据
    inputs, targets = next(iter(test_loader))

    # 如果 transforms 里面包含 crop 操作，则执行下面两行
    # bs, ncrops, c, h, w = np.shape(inputs)
    # inputs = inputs.view(-1, c, h, w)

    if use_cuda:
        inputs, targets = inputs.to(DEVICE), targets.to(DEVICE)
    inputs, targets = Variable(inputs), Variable(targets)

    net.eval()
    draw_features_of_net(net, inputs, img_name_pre=net_name+"_"+dataset)
    draw_weights_of_net(net, img_name_pre=net_name+"_"+dataset)
