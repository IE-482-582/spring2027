#!/usr/bin/env python3
"""
floating_image_demo.py

Swap the texture on the floating_image model at runtime by deleting
and respawning it with a new <albedo_map>.  Accepts a local file path
or a URL; URLs are downloaded first.

Supported formats: PNG, JPG/JPEG, BMP, TGA (Ogre2 native formats).
PNG is the only format that supports an alpha channel (transparency).

Usage:
    python3 floating_image_demo.py path/to/image.png
    python3 floating_image_demo.py https://example.com/target.jpg
    python3 floating_image_demo.py path/to/image.png --model my_float

Importable usage:
    from floating_image_demo import FloatingImage
    fi = FloatingImage(node, initial_name="floating_image")
    fi.set_image("path/to/image.png")
    fi.set_image("https://example.com/next.jpg")  # swaps again
"""

import argparse
import time
import urllib.request
from pathlib import Path

from gz.transport13 import Node
from gz.msgs10.boolean_pb2 import Boolean
from gz.msgs10.entity_factory_pb2 import EntityFactory
from gz.msgs10.entity_pb2 import Entity
from gz.msgs10.pose_pb2 import Pose


# Downloaded images are saved here so the path is reachable inside
# the Docker container (this directory is on the mounted volume).
DOWNLOAD_DIR = Path("/workspace/Projects/gazebo_demo/models/floating_image"
                    "/materials/textures")

SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tga"}

# Default pose / geometry — callers can override make_sdf() directly
DEFAULT_POSE  = "2 0 1 0 0 0"
DEFAULT_SIZE  = "2 2"
DEFAULT_WORLD = "default"


def download_image(url: str) -> Path:
    """Download *url* to DOWNLOAD_DIR, preserving the file extension.
    Returns the local Path."""
    suffix = Path(url.split("?")[0]).suffix.lower()  # strip query string first
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(
            f"Unsupported image format '{suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_SUFFIXES))}"
        )
    dest = DOWNLOAD_DIR / f"current_target{suffix}"
    print(f"Downloading {url} → {dest}")
    urllib.request.urlretrieve(url, dest)
    return dest


def resolve_image(path_or_url: str) -> Path:
    """Return a local Path, downloading first if *path_or_url* is a URL."""
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        return download_image(path_or_url)
    path = Path(path_or_url)
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError(
            f"Unsupported image format '{path.suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_SUFFIXES))}"
        )
    return path


def make_sdf(texture_path: Path, model_name: str) -> str:
    """Return an SDF string for the floating_image model."""
    return f"""<?xml version="1.0" ?>
<sdf version="1.10">
  <model name="{model_name}">
    <pose>{DEFAULT_POSE}</pose>
    <static>true</static>
    <link name="link">
      <visual name="visual">
        <pose>0 0 0 1.5708 0 0</pose>
        <geometry>
          <plane>
            <normal>1 0 0</normal>
            <size>{DEFAULT_SIZE}</size>
          </plane>
        </geometry>
        <material>
          <ambient>1 1 1 1</ambient>
          <diffuse>1 1 1 1</diffuse>
          <specular>0 0 0 1</specular>
          <double_sided>true</double_sided>
          <pbr>
            <metal>
              <albedo_map>file://{texture_path}</albedo_map>
              <metalness>0.0</metalness>
              <roughness>1.0</roughness>
            </metal>
          </pbr>
        </material>
      </visual>
    </link>
  </model>
</sdf>"""


def _request(node: Node, service: str, msg, RequestType, timeout_ms: int = 2000) -> None:
    """Call a gz-sim service and raise on failure."""
    ok, response = node.request(service, msg, RequestType, Boolean, timeout_ms)
    if not ok or not response.data:
        raise RuntimeError(
            f"Service call failed: {service}\n"
            "Confirm the world includes gz::sim::systems::UserCommands."
        )


class FloatingImage:
    """Manages a single floating image plane in a gz-sim world.

    Each call to set_image() removes the current model and spawns a
    replacement with a fresh, unique name.  Using a unique name on every
    spawn avoids the Ogre2 name-collision segfault that occurs when the
    same geometry name is re-registered before the renderer has finished
    removing the old one.

    Args:
        node:         gz-transport Node to use for service calls.
        initial_name: Name of the model already present in the world
                      (matches the <name> or <include> in the .world file).
        world:        gz-sim world name.
    """

    def __init__(
        self,
        node: Node,
        initial_name: str = "floating_image",
        world: str = DEFAULT_WORLD,
    ) -> None:
        self._node = node
        self._current_name = initial_name
        self._world = world
        self._counter = 0

    @property
    def current_name(self) -> str:
        return self._current_name

    def set_image(self, path_or_url: str) -> None:
        """Swap the displayed texture to *path_or_url* (file path or URL)."""
        texture_path = resolve_image(path_or_url)

        self._counter += 1
        new_name = f"floating_image_{self._counter}"

        # Move the current model underground rather than removing it.
        # gz-sim Harmonic has a rendering bug: deleting a model at runtime
        # orphans its Ogre2 visual, which then appears as a ghost at world
        # origin.  Sinking it below the ground plane is invisible to the
        # user and avoids the artifact entirely.
        hide_pose = Pose()
        hide_pose.name = self._current_name
        hide_pose.position.z = -100.0
        _request(self._node, f"/world/{self._world}/set_pose",
                 hide_pose, Pose)

        # Spawn replacement under a new unique name so Ogre2 never sees
        # a geometry name it already has registered.
        factory = EntityFactory()
        factory.sdf = make_sdf(texture_path, new_name)
        _request(self._node, f"/world/{self._world}/create", factory, EntityFactory)

        self._current_name = new_name
        print(f"Spawned '{new_name}' with texture: {texture_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("image", help="Local file path or URL of the image to display")
    parser.add_argument(
        "--model", default="floating_image",
        help="Name of the model currently in the world (default: floating_image)",
    )
    parser.add_argument(
        "--world", default=DEFAULT_WORLD,
        help=f"World name (default: {DEFAULT_WORLD})",
    )
    args = parser.parse_args()

    gz_node = Node()
    fi = FloatingImage(gz_node, initial_name=args.model, world=args.world)
    fi.set_image(args.image)
