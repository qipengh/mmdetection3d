import torch
import torch.nn.functional as F

from mmdet.models import DETECTORS
from .voxelnet import VoxelNet


@DETECTORS.register_module()
class DynamicVoxelNet(VoxelNet):
    """VoxelNet using `dynamic voxelization
    <https://arxiv.org/abs/1910.06528>`_."""

    def __init__(self,
                 voxel_layer,
                 voxel_encoder,
                 middle_encoder,
                 backbone,
                 neck=None,
                 bbox_head=None,
                 train_cfg=None,
                 test_cfg=None,
                 pretrained=None):
        super(DynamicVoxelNet, self).__init__(
            voxel_layer=voxel_layer,
            voxel_encoder=voxel_encoder,
            middle_encoder=middle_encoder,
            backbone=backbone,
            neck=neck,
            bbox_head=bbox_head,
            train_cfg=train_cfg,
            test_cfg=test_cfg,
            pretrained=pretrained,
        )

    def extract_feat(self, points, img_metas):
        """Extract features from points"""
        voxels, coors = self.voxelize(points)
        voxel_features, feature_coors = self.voxel_encoder(voxels, coors)
        batch_size = coors[-1, 0].item() + 1
        x = self.middle_encoder(voxel_features, feature_coors, batch_size)
        x = self.backbone(x)
        if self.with_neck:
            x = self.neck(x)
        return x

    @torch.no_grad()
    def voxelize(self, points):
        """Apply dynamic voxelization to points"""
        coors = []
        # dynamic voxelization only provide a coors mapping
        for res in points:
            res_coors = self.voxel_layer(res)
            coors.append(res_coors)
        points = torch.cat(points, dim=0)
        coors_batch = []
        for i, coor in enumerate(coors):
            coor_pad = F.pad(coor, (1, 0), mode='constant', value=i)
            coors_batch.append(coor_pad)
        coors_batch = torch.cat(coors_batch, dim=0)
        return points, coors_batch