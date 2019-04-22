# coding=utf-8
'''
本文件是该项目的main文件，定义了各个训练参数，以及不同数据集，不同网络的选择；
'''
import os
import torch
import torch.optim
from torch.autograd import Variable
import torch.nn as nn
import numpy as np
import argparse

from networks.ACNN import ACNN
from networks.ACCNN import ACCNN
from networks.AlexNet import AlexNet
from dal.JAFFE_DataSet import JAFFE
from dal.CKPlus48_DataSet import CKPlus48
from dal.FER2013_DataSet import FER2013
import transforms.transforms as transforms
import utils.utils as utils

use_cuda = torch.cuda.is_available()
DEVICE = torch.device("cuda" if use_cuda else "cpu")  # 让torch判断是否使用GPU，建议使用GPU环境，因为会快很多
enabled_nets = ["ACNN", "ACCNN", "AlexNet"]
enabled_datasets = ["JAFFE", "CK+48", "CK+", "FER2013"]

parser = argparse.ArgumentParser(description='PyTorch CNN Training With JAFFE')

# 模型选择
# parser.add_argument('--model', type=str, default='ACNN', help='CNN architecture')
parser.add_argument('--model', type=str, default='ACCNN', help='CNN architecture')
# parser.add_argument('--model', default='AlexNet', type=str, help='CNN architecture')

# 数据集选择
# parser.add_argument('--dataset', default='JAFFE', type=str, help='dataset')
parser.add_argument('--dataset', default='CK+48', type=str, help='dataset')
# parser.add_argument('--dataset', default='CK+', type=str, help='dataset')
# parser.add_argument('--dataset', default='FER2013', type=str, help='dataset')

# Other Parameters
# 存储的模型序号
parser.add_argument('--save_number', default=2, type=int, help='save_number')
# 批次大小
parser.add_argument('--bs', default=32, type=int, help='batch_size')
# 学习率
parser.add_argument('--lr', default=0.01, type=float, help='learning rate')
# epoch
parser.add_argument('--epoch', default=500, type=int, help='training epoch num')
# 每次获得到更优的准确率后，会进行一次存储，此选项选择是否从上次存储位置继续
parser.add_argument('--resume', default=True, type=bool, help='resume training from last checkpoint')
# 表示默认从第 $lrd_se 次epoch开始进行lr的递减，应该小于 $jump_out_epoch
parser.add_argument('--lrd_se', default=400, type=int, help='learning rate decay start epoch')
# 表示默认每经过2次epoch进行一次递减
parser.add_argument('--lrd_s', default=5, type=int, help='learning rate decay step')
# 表示每次的lr的递减率，默认每递减一次乘一次0.9
parser.add_argument('--lrd_r', default=0.9, type=float, help='learning rate decay rate')
opt = parser.parse_args()

train_acc_map = {'best_acc': 0, 'best_acc_epoch': -1, 0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
test_acc_map = {'best_acc': 0, 'best_acc_epoch': -1, 0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
Train_acc, Test_acc = 0., 0.


print("------------Preparing Model...----------------")
n_classes = 7
net_to_save_dir = "Saved_Models"
net_to_save_path = os.path.join(net_to_save_dir, opt.dataset + '_' + opt.model + "_" + str(opt.save_number))
saved_model_name = 'Best_model.t7'
if opt.model == "ACNN":
    net = ACNN(n_classes=n_classes).to(DEVICE)
elif opt.model == "ACCNN":
    net = ACCNN(n_classes=n_classes).to(DEVICE)
elif opt.model == "AlexNet":
    net = AlexNet(n_classes=n_classes).to(DEVICE)
else:
    net = None
    assert("opt.model should be in %s, but got %s" % (enabled_nets, opt.model))
start_epoch = 0
if opt.resume:
    # Load checkpoint.
    print('==> Loading Model Parameters...')
    if os.path.exists(os.path.join(net_to_save_path, saved_model_name)):
        assert os.path.isdir(net_to_save_path), 'Error: no checkpoint directory found!'
        checkpoint = torch.load(os.path.join(net_to_save_path, saved_model_name))
        net.load_state_dict(checkpoint['net'])
        test_acc_map['best_acc'] = checkpoint['best_test_acc']
        test_acc_map['best_acc_epoch'] = checkpoint['best_test_acc_epoch']
        start_epoch = test_acc_map['best_acc_epoch'] + 1
    else:
        print("Checkout File not Found, No initialization.")
print("------------%s Model Already be Prepared------------" % opt.model)

input_img_size = net.input_size
transform_train = transforms.Compose([
    transforms.Resize(input_img_size),  # 缩放将图片的最小边缩放为 input_img_size，因此如果输入是费正方形的，那么输出也不是正方形的
    transforms.RandomCrop(input_img_size),  # 用于将非正方形的图片进行处理
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
])

test_img_size = int(input_img_size * 1.1)  # 测试时，图片resize大小
transform_test = transforms.Compose([
    transforms.Resize(test_img_size),
    transforms.TenCrop(input_img_size),
    transforms.Lambda(lambda crops: torch.stack([transforms.ToTensor()(crop) for crop in crops])),
])

# criterion, target_type = nn.MSELoss(), 'fa'
criterion, target_type = nn.CrossEntropyLoss(), 'ls'
# 随机梯度下降
optimizer = torch.optim.SGD(net.parameters(), lr=opt.lr, momentum=0.9, weight_decay=5e-4)
# Adam 优化
# optimizer = torch.optim.Adam(net.parameters(), lr=opt.lr, weight_decay=5e-4)

print("------------Preparing Data...----------------")
if opt.dataset == "JAFFE":
    train_data = JAFFE(is_train=True, transform=transform_train, target_type=target_type)
    test_data = JAFFE(is_train=False, transform=transform_test, target_type=target_type)
elif opt.dataset == "CK+48":
    train_data = CKPlus48(is_train=True, transform=transform_train, target_type=target_type)
    test_data = CKPlus48(is_train=False, transform=transform_test, target_type=target_type)
elif opt.dataset == "CK+":
    train_data = CKPlus48(is_train=True, transform=transform_train, target_type=target_type, img_dir_pre_path="data/CK+")
    test_data = CKPlus48(is_train=False, transform=transform_test, target_type=target_type, img_dir_pre_path="data/CK+")
elif opt.dataset == "FER2013":
    train_data = FER2013(is_train=True, private_test=True, transform=transform_train, target_type=target_type)
    test_data = FER2013(is_train=False, private_test=True, transform=transform_test, target_type=target_type)
else:
    assert("opt.dataset should be in %s, but got %s" % (enabled_datasets, opt.dataset))
train_loader = torch.utils.data.DataLoader(train_data, batch_size=opt.bs, shuffle=True)
test_loader = torch.utils.data.DataLoader(test_data, batch_size=opt.bs, shuffle=False)
print("------------%s Data Already be Prepared------------" % opt.dataset)


# Training
def train(epoch, jump_out_lr=-1.):
    print('\n------------Epoch: %d-------------' % epoch)
    # 根据训练的epoch次数来降低learning rate
    if epoch > opt.lrd_se > 0:
        frac = (epoch - opt.lrd_se) // opt.lrd_s
        decay_factor = opt.lrd_r ** frac
        current_lr = opt.lr * decay_factor  # current_lr = opt.lr * 降低率 ^ ((epoch - 开始decay的epoch) // 每次decay的epoch num)
        utils.set_lr(optimizer, current_lr)  # set the learning rate
    else:
        current_lr = opt.lr
    print('learning_rate: %s' % str(current_lr))
    global Train_acc
    net.train()
    train_loss = 0
    correct = 0
    total = 0
    cur_train_acc = 0.
    for batch_idx, (inputs, targets) in enumerate(train_loader):
        if use_cuda:
            inputs, targets = inputs.to(DEVICE), targets.to(DEVICE, torch.long)
        optimizer.zero_grad()
        inputs, targets = Variable(inputs), Variable(targets)
        outputs = net(inputs)
        # print("outputs:", outputs)
        # print("targets:", targets)
        loss = criterion(outputs, targets)
        loss.backward()
        # utils.clip_gradient(optimizer, 0.1)
        optimizer.step()

        train_loss += loss.data
        _, predicted = torch.max(outputs.data, 1)  # torch.max() 加上dim参数后，返回值为 max_value, max_value_index
        if target_type == 'ls':
            ground_value = targets.data
        elif target_type == 'fa':
            _, ground_value = torch.max(targets.data, 1)
        # print("predicted:", predicted)
        # print("ground_value:", ground_value)

        for i in range(len(predicted)):
            if predicted[i] == ground_value[i]:
                train_acc_map[predicted[i].item()] += 1

        total += targets.size(0)
        correct += predicted.eq(ground_value.data).cpu().sum()
        # print("equal: ", predicted.eq(ground_value.data).cpu())
        cur_train_acc = (100. * correct / total).item()

        utils.progress_bar(batch_idx, len(train_loader), 'Loss: %.3f | Acc: %.3f%% (%d/%d)' %
                           (train_loss / (batch_idx + 1), cur_train_acc, correct, total))

    Train_acc = cur_train_acc
    if train_acc_map['best_acc'] < Train_acc:
        train_acc_map['best_acc'] = Train_acc
        train_acc_map['best_acc_epoch'] = epoch


# Testing
def test(epoch):
    global Test_acc
    private_test_loss = 0
    net.eval()
    correct = 0
    total = 0
    cur_test_acc = 0.
    correct_map = [0, 0, 0, 0, 0, 0, 0]
    with torch.no_grad():
        for batch_idx, (inputs, targets) in enumerate(test_loader):
            bs, ncrops, c, h, w = np.shape(inputs)
            inputs = inputs.view(-1, c, h, w)

            if use_cuda:
                inputs, targets = inputs.to(DEVICE), targets.to(DEVICE)
            inputs, targets = Variable(inputs), Variable(targets)
            outputs = net(inputs)
            outputs_avg = outputs.view(bs, ncrops, -1).mean(1)  # avg over crops

            loss = criterion(outputs_avg, targets)
            private_test_loss += loss.data
            _, predicted = torch.max(outputs_avg.data, 1)
            if target_type == 'ls':
                ground_value = targets.data
            elif target_type == 'fa':
                _, ground_value = torch.max(targets.data, 1)

            for i in range(len(predicted)):
                if predicted[i] == ground_value[i]:
                    c = predicted[i].item()
                    test_acc_map[c] += 1
                    correct_map[c] += 1

            total += targets.size(0)
            correct += predicted.eq(ground_value.data).cpu().sum()
            cur_test_acc = (100. * correct / total).item()

            utils.progress_bar(batch_idx, len(test_loader), 'Loss: %.3f | Acc: %.3f%% (%d/%d)'
                         % (private_test_loss / (batch_idx + 1), cur_test_acc, correct, total))

    Test_acc = cur_test_acc
    if test_acc_map['best_acc'] < Test_acc:
        test_acc_map['best_acc'] = Test_acc
        test_acc_map['best_acc_epoch'] = epoch
        print('Saving net to %s' % net_to_save_path)
        print('best_acc: %0.3f' % test_acc_map['best_acc'])
        print('correct_map: %s' % correct_map)
        state = {'net': net.state_dict() if use_cuda else net,
                 'best_test_acc': test_acc_map['best_acc'],
                 'best_test_acc_epoch': test_acc_map['best_acc_epoch'],
                 'correct_map': correct_map,
                 }
        if not os.path.isdir(net_to_save_dir):
            os.mkdir(net_to_save_dir)
        if not os.path.isdir(net_to_save_path):
            os.mkdir(net_to_save_path)
        torch.save(state, os.path.join(net_to_save_path, saved_model_name))


if __name__ == "__main__":

    for epoch in range(start_epoch, opt.epoch, 1):
        train(epoch)
        # for parameters in net.parameters():
        #     print(parameters.size())
        #     print(parameters[0][0][0])
        #     break

        # for name,parameters in net.named_parameters():
        #     print(name,':',parameters.size())
        #     print(parameters)
        #     break
        test(epoch)
    print(train_acc_map)
    print(test_acc_map)