exp_name = '001_ciaosr_rdn_div2k'
scale_min, scale_max = 1, 4
val_scale = 4 
data_type = ''  

from mmedited.models.restorers.ciaosr import CiaoSR
from mmedited.models.backbones.sr_backbones.ciaosr_net import LocalImplicitSRRDN


# model settings
model = dict(
    type=CiaoSR,
    generator=dict(
        type=LocalImplicitSRRDN,
        encoder=dict(
            type='RDN',
            in_channels=3,
            out_channels=3,
            mid_channels=64,
            num_blocks=16,
            upscale_factor=4,
            num_layers=8,
            channel_growth=64),
        imnet_q=dict(
            type='MLPRefiner',
            in_dim=4,
            out_dim=3,
            hidden_list=[256, 256, 256, 256]),
        imnet_k=dict(
            type='MLPRefiner',
            in_dim=64,
            out_dim=64,
            hidden_list=[256, 256, 256, 256]),
        imnet_v=dict(
            type='MLPRefiner',
            in_dim=64,
            out_dim=64,
            hidden_list=[256, 256, 256, 256]),
        feat_unfold=True,
        eval_bsize=30000,
        ),
    rgb_mean=(0.4488, 0.4371, 0.4040),
    rgb_std=(1., 1., 1.),
    pixel_loss=dict(type='L1Loss', loss_weight=1.0, reduction='mean'))
# model training and testing settings
train_cfg = None
if val_scale <= 4:
    test_cfg = dict(metrics=None, crop_border=val_scale, scale=val_scale, tile=192, tile_overlap=32, convert_to='y') # larger tile is better
else:
    test_cfg = dict(metrics=None, crop_border=val_scale, scale=val_scale, convert_to='y') # x6, x8, x12 

# dataset settings
train_dataset_type = 'SRFolderGTDataset'
val_dataset_type = 'SRFolderGTDataset'
test_dataset_type = 'SRFolderDataset'
train_pipeline = [
    dict(
        type='LoadImageFromFile',
        io_backend='disk',
        key='gt',
        flag='color',
        channel_order='rgb'),
    dict(
        type='RandomDownSampling',
        scale_min=scale_min,
        scale_max=scale_max,
        patch_size=48),
    dict(type='RescaleToZeroOne', keys=['lq', 'gt']),
    dict(
        type='Flip', keys=['lq', 'gt'], flip_ratio=0.5,
        direction='horizontal'),
    dict(type='Flip', keys=['lq', 'gt'], flip_ratio=0.5, direction='vertical'),
    dict(type='RandomTransposeHW', keys=['lq', 'gt'], transpose_ratio=0.5),
    dict(type='ImageToTensor', keys=['lq', 'gt']),
    dict(type='GenerateCoordinateAndCell', sample_quantity=2304),
    dict(
        type='Collect',
        keys=['lq', 'gt', 'coord', 'cell'],
        meta_keys=['gt_path'])
]


valid_pipeline = [
    dict(
        type='LoadImageFromFile',
        io_backend='disk',
        key='gt',
        flag='color',
        channel_order='rgb'),
    dict(type='RandomDownSampling', scale_min=val_scale, scale_max=val_scale),  
    dict(type='RescaleToZeroOne', keys=['lq', 'gt']),
    dict(type='ImageToTensor', keys=['lq', 'gt']),
    dict(type='GenerateCoordinateAndCell', scale=val_scale),  
    dict(
        type='Collect',
        keys=['lq', 'gt', 'coord', 'cell'],
        meta_keys=['gt_path'])
]

test_pipeline = [
    dict(
        type='LoadImageFromFile',
        io_backend='disk',
        key='lq',
        flag='color',
        channel_order='rgb'),
    dict(type='RescaleToZeroOne', keys=['lq']),
    dict(type='ImageToTensor', keys=['lq']),
    dict(type='GenerateCoordinateAndCell', scale=val_scale),
    dict(
        type='Collect',
        keys=['lq', 'coord', 'cell'],
        meta_keys=['lq_path'])
]

data_dir = "data"
lq_path = f'{data_dir}' + '/LR'
gt_path = f'{data_dir}/Classical/' + '/GTmod12'

data = dict(
    workers_per_gpu=8,
    train_dataloader=dict(samples_per_gpu=16, drop_last=True),
    val_dataloader=dict(samples_per_gpu=1),
    test_dataloader=dict(samples_per_gpu=1),
    train=dict(
        type='RepeatDataset',
        times=20,
        dataset=dict(
            type=train_dataset_type,
            gt_folder=f'{data_dir}/DIV2K/HR',  
            pipeline=train_pipeline,
            scale=scale_max)),
    val=dict(type=val_dataset_type,
             gt_folder=gt_path, 
             pipeline=valid_pipeline,
             scale=scale_max),
    test=dict(
        type=test_dataset_type,
        lq_folder=lq_path,
        gt_folder=gt_path, 
        pipeline=test_pipeline,  
        scale=val_scale,
        filename_tmpl='{}') if val_scale <= 4 else 
            dict(type=val_dataset_type, 
                 gt_folder=gt_path, 
                 pipeline=valid_pipeline, 
                 scale=val_scale)
    ) 

# optimizer
optimizers = dict(type='Adam', lr=1.e-4)

# learning policy
iter_per_epoch = 1000
total_iters = 1000 * iter_per_epoch
lr_config = dict(
    policy='Step',
    by_epoch=False,
    step=[200000, 400000, 600000, 800000],
    gamma=0.5)

checkpoint_config = dict(interval=3000, save_optimizer=True, by_epoch=False)
evaluation = dict(interval=3000, save_image=False, gpu_collect=True)
log_config = dict(
    interval=100,
    hooks=[
        dict(type='TextLoggerHook', by_epoch=False),
        dict(type='TensorboardLoggerHook')
    ])
visual_config = None

run_dir = './work_dirs'
# runtime settings
dist_params = dict(backend='nccl')
log_level = 'INFO'
work_dir = f'{run_dir}/{exp_name}'
load_from = None
resume_from = None
workflow = [('train', 1)]
find_unused_parameters = True
test_checkpoint_path = f'{run_dir}/{exp_name}/latest.pth' # use --checkpoint None to enable this path in testing
