#!/usr/bin/env python
# -*- coding: utf-8 -*-
import numpy as np
from numpy import *
# from scipy.misc import imresize
from skimage.measure import compare_ssim
import cv2
import glob
import time
import os
import argparse
import  Net.MGANet as MGANet

import torch
import copy
def yuv_import(filename, dims ,startfrm,numframe):
    fp = open(filename, 'rb')
    frame_size = np.prod(dims) * 3 / 2
    fp.seek(0, 2)

    ps = fp.tell()
    totalfrm = int(ps // frame_size)
    d00 = dims[0] // 2
    d01 = dims[1] // 2

    assert startfrm+numframe<=totalfrm

    Y = np.zeros(shape=(numframe, 1,dims[0], dims[1]), dtype=np.uint8, order='C')
    U = np.zeros(shape=(numframe, 1,d00, d01),dtype= np.uint8, order='C')
    V = np.zeros(shape=(numframe, 1,d00, d01),dtype= np.uint8, order='C')



    fp.seek(int(frame_size * startfrm), 0)
    for i in range(startfrm,startfrm+numframe):
        for m in range(dims[0]):
            for n in range(dims[1]):
                Y[i-startfrm,0, m, n] = ord(fp.read(1))
        for m in range(d00):
            for n in range(d01):
                U[i-startfrm,0, m, n] = ord(fp.read(1))
        for m in range(d00):
            for n in range(d01):
                V[i-startfrm,0, m, n] = ord(fp.read(1))

    fp.close()
    Y = Y.astype(np.float32)
    U = U.astype(np.float32)
    V = V.astype(np.float32)
    return Y, U, V

def get_w_h(filename):
    width = int((filename.split('x')[0]).split('_')[-1])
    height = int((filename.split('x')[1]).split('_')[0])

    return (height,width)

def get_data(one_filename,video_index,num_frame,startfrm_position):


    one_filename_length = len(one_filename)
    data_Y = []
    for i in range(one_filename_length+1):
        if i == 0:
            data_37_filename = np.sort(glob.glob(one_filename[i]+'/*.yuv'))
            data_37_filename_length = len(data_37_filename )
            for i_0 in range(video_index,video_index+1):
                file_name = data_37_filename[i_0]
                dims = get_w_h(filename=file_name)
                data_37_filename_Y,data_37_filename_U,data_37_filename_V = yuv_import(filename=file_name, dims=dims ,startfrm=startfrm_position,numframe=num_frame)
                data_Y.append(data_37_filename_Y)
               
        if i == 1:
            mask_37_filename = np.sort(glob.glob(one_filename[i] + '/*.yuv'))
            mask_37_filename_length = len(mask_37_filename)
            for i_1 in range(video_index,video_index+1):
                file_name = mask_37_filename[i_1]
                dims = get_w_h(filename=file_name)
                mask_37_filename_Y, mask_37_filename_U, mask_37_filename_V = yuv_import(filename=file_name, dims=dims,startfrm=startfrm_position, numframe=num_frame)
                data_Y.append(mask_37_filename_Y)
        if i == 2:
            label_37_filename = np.sort(glob.glob('./testing_set/label/' + '*.yuv'))
            label_37_filename_length = len(label_37_filename)
            for i_2 in range(video_index,video_index+1):
                file_name = label_37_filename[i_2]
                dims = get_w_h(filename=file_name)
                label_37_filename_Y, label_37_filename_U, label_37_filename_V = yuv_import(filename=file_name, dims=dims,startfrm=startfrm_position, numframe=num_frame)
                data_Y.append(label_37_filename_Y)
               
    return  data_Y

def test_batch(data_Y, start, batch_size=1):

    data_pre = (data_Y[0][start-1:start,...])/255.0
    data_cur = data_Y[0][start:start+1,...]/255.0
    data_aft = data_Y[0][start+1:start+2,...]/255.0

    mask     = data_Y[1][start:start+1,...]/255.0
    label    = data_Y[2][start:start+1,...]

    start+=1
    return  data_pre,data_cur,data_aft,mask,label,start

def PSNR(img1, img2):
    mse = np.mean( (img1.astype(np.float32) - img2.astype(np.float32)) ** 2 ).astype(np.float32)
    if mse == 0:
        return 100
    PIXEL_MAX = 255.0
    return 20 * math.log10(PIXEL_MAX / math.sqrt(mse))

def image_test(one_filename,net_G,patch_size=[128,128],f_txt=None,opt=None):

    
    ave_gain_psnr    =0.
    ave_psnr_predict  =0.
    ave_psnr_data =0.
    video_num=opt.video_nums
    for video_index in range(video_num):
        data_37_filename = np.sort(glob.glob(one_filename[0]+'/*.yuv'))
        data_Y = get_data(one_filename,video_index=video_index,num_frame=opt.frame_nums+5,startfrm_position=opt.startfrm_position)
        start =1

        psnr_gain_sum = 0
        psnr_pre_gt_sum=0
        psnr_data_gt_sum=0
        nums =opt.frame_nums
        for itr in range(0, nums):
            data_pre, data_cur, data_aft, mask, label, start = test_batch(data_Y=data_Y, start=start, batch_size=opt.batch_size)

            height = data_pre.shape[2]
            width = data_pre.shape[3]

            data_pre_value_patch = torch.from_numpy(data_pre).float()
            data_cur_value_patch = torch.from_numpy(data_cur).float()
            data_aft_value_patch = torch.from_numpy(data_aft).float()
            data_mask_value_patch = torch.from_numpy(mask).float()

            if opt.channels_last:
                data_pre_value_patch = data_pre_value_patch.contiguous(memory_format=torch.channels_last)
                data_cur_value_patch = data_cur_value_patch.contiguous(memory_format=torch.channels_last)
                data_aft_value_patch = data_aft_value_patch.contiguous(memory_format=torch.channels_last)
                data_mask_value_patch = data_mask_value_patch.contiguous(memory_format=torch.channels_last)

            # H2D
            h2d_time = time.time()
            data_pre_value_patch.to(opts.device)
            data_cur_value_patch.to(opts.device)
            data_aft_value_patch.to(opts.device)
            data_mask_value_patch.to(opts.device)
            h2d_time = time.time() - h2d_time
            print("H2D time: {} sec".format(h2d_time))

            if opt.compile:
                data_pre_value_patch = torch.compile(data_pre_value_patch, backend=opt.backend, options={"freezing": True})
                data_cur_value_patch = torch.compile(data_cur_value_patch, backend=opt.backend, options={"freezing": True})
                data_aft_value_patch = torch.compile(data_aft_value_patch, backend=opt.backend, options={"freezing": True})
                data_mask_value_patch = torch.compile(data_mask_value_patch, backend=opt.backend, options={"freezing": True})
                
            total_time = 0.0
            total_sample = 0
            for i in range(opt.num_iter):
                elapsed = time.time()
                fake_image = net_G(data_pre_value_patch,data_cur_value_patch,data_aft_value_patch,data_mask_value_patch)
                if torch.cuda.is_available(): torch.cuda.synchronize()
                elapsed = time.time() - elapsed
                if opt.profile:
                    opt.p.step()
                print("Iteration: {}, inference time: {} sec.".format(i, elapsed + h2d_time), flush=True)
                if i >= opt.num_warmup:
                    total_time += elapsed + h2d_time
                    total_sample += 1

                fake_image_numpy = fake_image.float().detach().cpu().numpy()
                fake_image_numpy = np.squeeze(fake_image_numpy)*255.0

            throughput = total_sample / total_time
            latency = total_time / total_sample * 1000
            print('inference latency: %.3f ms' % latency)
            print('inference Throughput: %f samples/s' % throughput)

            finally_image=np.squeeze(fake_image_numpy)
            mask_image = np.squeeze(mask)*255.
            os.makedirs(opt.result_path+'/result_enhanced_data/%02d'%(video_index+1),exist_ok = True)
            os.makedirs(opt.result_path+'/result_mask/%02d'%(video_index+1),exist_ok = True)
            os.makedirs(opt.result_path+'/result_label/%02d'%(video_index+1),exist_ok = True)
            os.makedirs(opt.result_path+'/result_compression_data/%02d'%(video_index+1),exist_ok = True)
            cv2.imwrite(opt.result_path+'/result_enhanced_data/%02d/%02d.png'%(video_index+1,itr+2),finally_image.astype(np.uint8))
            cv2.imwrite(opt.result_path+'/result_mask/%02d/%02d.png'%(video_index+1,itr+2),mask_image.astype(np.uint8))
            data_cur_image = (np.squeeze(data_cur)*255.0).astype(np.float32)
            label = np.squeeze(label).astype(np.float32)
            cv2.imwrite(opt.result_path+'/result_label/%02d/%02d.png'%(video_index+1,itr+2),label.astype(np.uint8))
            cv2.imwrite(opt.result_path+'/result_compression_data/%02d/%02d.png'%(video_index+1,itr+2),data_cur_image.astype(np.uint8))

            psnr_pre_gt  = PSNR(finally_image, label)

            psnr_data_gt = PSNR(data_cur_image, label)

            psnr_gain = psnr_pre_gt - psnr_data_gt
            psnr_gain_sum +=psnr_gain
            psnr_pre_gt_sum+=psnr_pre_gt
            psnr_data_gt_sum+=psnr_data_gt
            print('psnr_gain:%.05f'%(psnr_gain))
            print('psnr_predict:{:.04f} psnr_anchor:{:.04f}  psnr_gain:{:.04f}'.format(psnr_pre_gt,psnr_data_gt,psnr_gain),file=f_txt)
            break

        print( data_37_filename[video_index])
        print('video_index:{:2d} psnr_predict_average:{:.04f} psnr_data_average:{:.04f}  psnr_gain_average:{:.04f}'.format(video_index,psnr_pre_gt_sum/nums,psnr_data_gt_sum/nums,psnr_gain_sum/nums),file=f_txt)
        print('{}'.format(data_37_filename[video_index]),file=f_txt)
        f_txt.write('\r\n')
        ave_gain_psnr+=psnr_gain_sum/nums
        ave_psnr_predict  +=psnr_pre_gt_sum/nums
        ave_psnr_data +=psnr_data_gt_sum/nums
        break

    print(' average_psnr_predict:{:.04f} average_psnr_anchor:{:.04f}  average_psnr_gain:{:0.4f}'.format(ave_psnr_predict/video_num,ave_psnr_data/video_num,ave_gain_psnr/video_num))
    print(' average_psnr_predict:{:.04f} average_psnr_anchor:{:.04f}  average_psnr_gain:{:0.4f}'.format(ave_psnr_predict/video_num,ave_psnr_data/video_num,ave_gain_psnr/video_num), file=f_txt)




if __name__ == "__main__":
   
    parser = argparse.ArgumentParser(description="MGANet_test")
    parser.add_argument('--net_G', default='./models/MGANet_model_AI37.pth',help="add checkpoint")
    parser.add_argument("--gpu_id", default=0, type=int, help="gpu ids (default: 0)")
    parser.add_argument("--video_nums", default=1, type=int, help="Videos number (default: 0)")
    parser.add_argument("--frame_nums", default=29, type=int, help="frame number of the video to test (default: 90)")
    parser.add_argument("--startfrm_position", default=9, type=int, help="start frame position in one video (default: 0)")
    parser.add_argument("--is_training", default=False, type=bool, help="train or test mode")
    parser.add_argument("--result_path", default='./result_AI37/', type=str, help="store results")
    # for oob
    parser.add_argument("--device", default='cpu', type=str, help="device")
    parser.add_argument("--batch_size", default=1, type=int, help="batch_size")
    parser.add_argument('--precision', type=str, default='float32', help='precision')
    parser.add_argument('--channels_last', type=int, default=1, help='use channels last format')
    parser.add_argument('--num_iter', type=int, default=-1, help='num_iter')
    parser.add_argument('--num_warmup', type=int, default=-1, help='num_warmup')
    parser.add_argument('--profile', dest='profile', action='store_true', help='profile')
    parser.add_argument('--quantized_engine', type=str, default=None, help='quantized_engine')
    parser.add_argument('--ipex', dest='ipex', action='store_true', help='ipex')
    parser.add_argument('--jit', dest='jit', action='store_true', help='jit')
    parser.add_argument("--compile", action='store_true', default=False,
                    help="enable torch.compile")
    parser.add_argument("--backend", type=str, default='inductor',
                    help="enable torch.compile backend")
    opts = parser.parse_args()
    opts.result_path = opts.result_path + str(os.getpid())
    # torch.cuda.set_device(opts.gpu_id)

    txt_name = opts.result_path + '/MGANet_test_data_AI37.txt'

    if os.path.isfile(txt_name):
        f = open(txt_name, 'w+')  
    else:
        os.makedirs(opts.result_path, exist_ok = True)
        os.mknod(txt_name)
        f = open(txt_name, 'w+')

    one_filename = np.sort(glob.glob('./testing_set/AI37/' + '*'))
    print(one_filename)
   
    patch_size =[240,416]
    net_G = MGANet.Gen_Guided_UNet(batchNorm=False,input_size=patch_size,is_training=opts.is_training)
    net_G.eval()
    net_G.load_state_dict(torch.load(opts.net_G, map_location='cpu'))
    print('....')
    net_G.to(opts.device)
    # NHWC
    if opts.channels_last:
        net_G = net_G.to(memory_format=torch.channels_last)
        print("---- Use NHWC model")

    if opts.profile:
        def trace_handler(p):
            output = p.key_averages().table(sort_by="self_cpu_time_total")
            print(output)
            import pathlib
            timeline_dir = str(pathlib.Path.cwd()) + '/timeline/'
            if not os.path.exists(timeline_dir):
                try:
                    os.makedirs(timeline_dir)
                except:
                    pass
            timeline_file = timeline_dir + 'timeline-' + str(torch.backends.quantized.engine) + '-' + \
                        'MGANet-DCC2020-' + str(p.step_num) + '-' + str(os.getpid()) + '.json'
            p.export_chrome_trace(timeline_file)
        with torch.profiler.profile(
            activities=[torch.profiler.ProfilerActivity.CPU, torch.profiler.ProfilerActivity.CUDA],
            record_shapes=True,
            schedule=torch.profiler.schedule(
                wait=int(opts.num_iter/2),
                warmup=2,
                active=1,
            ),
            on_trace_ready=trace_handler,
        ) as p:
            opts.p = p
            if opts.precision == "bfloat16":
                print('---- Enable AMP bfloat16')
                with torch.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu", enabled=True, dtype=torch.bfloat16):
                    image_test(one_filename=one_filename,net_G=net_G,patch_size=patch_size,f_txt = f,opt = opts)
            elif opts.precision == "float16":
                print('---- Enable AMP float16')
                with torch.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu", enabled=True, dtype=torch.half):
                    image_test(one_filename=one_filename,net_G=net_G,patch_size=patch_size,f_txt = f,opt = opts)
            else:
                image_test(one_filename=one_filename,net_G=net_G,patch_size=patch_size,f_txt = f,opt = opts)
    else:
        if opts.precision == "bfloat16":
            print('---- Enable AMP bfloat16')
            with torch.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu", enabled=True, dtype=torch.bfloat16):
                image_test(one_filename=one_filename,net_G=net_G,patch_size=patch_size,f_txt = f,opt = opts)
        elif opts.precision == "float16":
            print('---- Enable AMP float16')
            with torch.autocast(device_type="cuda" if torch.cuda.is_available() else "cpu", enabled=True, dtype=torch.half):
                image_test(one_filename=one_filename,net_G=net_G,patch_size=patch_size,f_txt = f,opt = opts)
        else:
            image_test(one_filename=one_filename,net_G=net_G,patch_size=patch_size,f_txt = f,opt = opts)

    f.close()
  


