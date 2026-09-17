import torch.nn as nn
import torchvision.models as tv_models

# These constants are shared by every script in the project (the server, the
# dataset generator, training, and both solvers) so they all agree on exactly
# what a CAPTCHA looks like.
CHARSET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
CAPTCHA_LENGTH = 5
IMG_WIDTH = 160
IMG_HEIGHT = 64


class CaptchaSolver(nn.Module):
    """Reads a whole CAPTCHA image at once, with no letter segmentation step.

    This is a fine-tuned ResNet18 instead of a from-scratch CNN. A from-scratch
    network has to learn what a letter even looks like using only our own
    generated images; ResNet18 already knows how to see (edges, curves,
    shapes) from being pretrained on ~1.2M real ImageNet photos, so it only
    has to adapt that existing knowledge to this noise/distortion style. That's
    what took the live solve rate from ~60% to ~92-96% (see README).
    """

    def __init__(self):
        super().__init__()
        resnet = tv_models.resnet18(weights=tv_models.ResNet18_Weights.IMAGENET1K_V1)

        # ResNet18 was pretrained on 3-channel color photos, but our CAPTCHAs
        # are grayscale. Rather than discard the pretrained first layer, we
        # average its 3 color-channel filters into 1, keeping the pretrained
        # edge/texture detectors while accepting 1-channel input.
        old_conv1 = resnet.conv1
        new_conv1 = nn.Conv2d(
            1, old_conv1.out_channels, kernel_size=old_conv1.kernel_size,
            stride=old_conv1.stride, padding=old_conv1.padding, bias=False,
        )
        new_conv1.weight.data = old_conv1.weight.data.mean(dim=1, keepdim=True)
        resnet.conv1 = new_conv1

        # Drop ResNet's original 1000-way ImageNet classifier — we don't want
        # "is this a dog or a car", we want the raw 512-d feature vector.
        resnet.fc = nn.Identity()

        self.backbone = resnet
        # One classification head per character position, since every
        # CAPTCHA here is a fixed length. Each head independently picks one
        # of the 36 possible characters for its position.
        self.heads = nn.ModuleList([nn.Linear(512, len(CHARSET)) for _ in range(CAPTCHA_LENGTH)])

    def forward(self, x):
        features = self.backbone(x)
        return [head(features) for head in self.heads]
