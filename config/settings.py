# settings.py

import json
import os

settings_file = "app_settings.json"

current_settings = {
    "night_mode": False,
    "point_size": 1.0,  # Default point size
    "show_full_view": True,
    "show_cluster_view": True,
    "eco_mode": False,
    "num_classes": 3,
    "superpoint_graph": "mst",
    "KNN_graph": 8,
    "Subsampling": "bucket_fps_kdline_medium",
    "Subsample_size": 2048,
    "Community_detection": "label_propagation",
}


def load_settings():
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r") as file:
                return json.load(file)
        except json.JSONDecodeError:
            pass
    return current_settings


def save_settings(settings):
    with open(settings_file, "w") as file:
        json.dump(settings, file, indent=4)


# Initialize settings on import
current_settings = load_settings()
