from __future__ import annotations

import os
from pathlib import Path


def get_env(name: str, *, default: str) -> str:
    return os.environ.get(name, default)


def get_env_int(name: str, *, default: int) -> int:
    return int(get_env(name, default=str(default)))


def get_env_float(name: str, *, default: float) -> float:
    return float(get_env(name, default=str(default)))


def get_env_path(name: str, *, default: str) -> Path:
    return Path(get_env(name, default=default))


VISION_FOOD_MODEL_ID = get_env("VISION_FOOD_MODEL_ID", default="nateraw/food")
VISION_FOOD_MODEL_REVISION = get_env(
    "VISION_FOOD_MODEL_REVISION",
    default="ddbd0f9ed493f03fc6a45527e5e52904161d3e09",
)
VISION_FOOD_MODEL_TOP_K = get_env_int("VISION_FOOD_MODEL_TOP_K", default=1)
VISION_FOOD_MODEL_LOW_CONFIDENCE_THRESHOLD = get_env_float(
    "VISION_FOOD_MODEL_LOW_CONFIDENCE_THRESHOLD",
    default=0.50,
)
VISION_FOOD_DETECTOR_MODEL_ID = get_env(
    "VISION_FOOD_DETECTOR_MODEL_ID",
    default="IDEA-Research/grounding-dino-tiny",
)
VISION_FOOD_DETECTOR_MODEL_REVISION = get_env(
    "VISION_FOOD_DETECTOR_MODEL_REVISION",
    default="a2bb814dd30d776dcf7e30523b00659f4f141c71",
)
VISION_FOOD_DETECTOR_THRESHOLD = get_env_float(
    "VISION_FOOD_DETECTOR_THRESHOLD",
    default=0.25,
)
VISION_FOOD_DETECTOR_TEXT_THRESHOLD = get_env_float(
    "VISION_FOOD_DETECTOR_TEXT_THRESHOLD",
    default=0.20,
)
VISION_FOOD_DETECTOR_MAX_REGIONS = get_env_int(
    "VISION_FOOD_DETECTOR_MAX_REGIONS",
    default=8,
)
VISION_FOOD_DETECTOR_NMS_THRESHOLD = get_env_float(
    "VISION_FOOD_DETECTOR_NMS_THRESHOLD",
    default=0.60,
)
VISION_FOOD_DETECTOR_LABELS = tuple(
    label.strip()
    for label in get_env(
        "VISION_FOOD_DETECTOR_LABELS",
        default=(
            "food,dish,bread,strawberry,milkshake,pear,rice,chicken,asparagus,broccoli,"
            "sausage,noodles,mushroom,onion,carrot,tofu,snow peas,fish,potato,cauliflower,"
            "steak,spring onion,egg,salad,pasta,pizza,soup,meat,fruit,vegetable,dessert,"
            "drink,cheese,sauce"
        ),
    ).split(",")
    if label.strip()
)
VISION_LOCAL_PRIVATE_MEDIA_ROOT = get_env_path(
    "VISION_LOCAL_PRIVATE_MEDIA_ROOT",
    default="/app/local_uploads/private",
)
