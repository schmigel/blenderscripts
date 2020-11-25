print("=============================================================")

import sys
import bpy
import json
import os.path
import requests
from dataclasses import dataclass
from math import radians
import argparse

@dataclass
class Vector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

@dataclass
class Transform:
    position: Vector3
    rotation: Vector3
    scale: Vector3

@dataclass
class SceneObject:
    objtype: str
    mesh_id: str
    transform: []

@dataclass
class Camera:
    objtype: str
    FOV: float
    transform: []

@dataclass
class Light:
    objtype: str
    intensity: float
    radius: float
    transform: []

@dataclass
class Scene:
    id: str
    objects: []
    cameras: []
    lights: []

# Get arguments -----------------------

print()
print(sys.argv)
print()

try:
    args = list(reversed(sys.argv))
    print("\nListReversed args = ")
    print(list(reversed(sys.argv)))
    params = args[1]
    params = params[params.index("=")+1:]

except ValueError:
    params = []
    

print("\nScript params:", params)

#---------------------------------------

# Translate Scene information from JSON -----------------------
print(os.path.abspath(os.path.curdir))

scene = Scene(None, [], [], [])

# with open ('revire/scenebuilder/1574253591.json') as json_file:
data = json.loads(params)

print(data['sceneList'][0]['objects'][0])
print("Adding Objects to scene")
for obj in data['sceneList'][0]['objects']:
    scene_obj = SceneObject(
        obj["type"],
        obj["mesh_id"],
        Transform(
            Vector3(*obj["transform"]["location"]),
            Vector3(*obj["transform"]["rotation"]),
            Vector3(*obj["transform"]["scale"])
            )
        )
    scene.objects.append(scene_obj)

print("Adding Cameras to scene")
for obj in data['sceneList'][0]['cameras']:
    if(obj["type"] == "camera"):
        scene_camera = Camera(
            obj["type"],
            obj["fov"],
            Transform(
                Vector3(*obj["transform"]["location"]),
                Vector3(*obj["transform"]["rotation"]),
                Vector3(*obj["transform"]["scale"])
                )
            )
        scene.cameras.append(scene_camera)

print("Adding Lights to scene")
for obj in data['sceneList'][0]['lights']:
    scene_light = Light(
        obj["type"],
        obj["intensity"],
        obj["radius"],
        Transform(
            Vector3(*obj["transform"]["location"]),
            Vector3(*obj["transform"]["rotation"]),
            Vector3(*obj["transform"]["scale"])
            )
        )
    scene.lights.append(scene_light)
scene.id = data['_id']
        
print(scene)
print("Setting up")
#---------------------------------------------------------------

#Setup Scene properties ---------------
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 0.01
#bpy.context.space_data.clip_end = 100000
# bpy.context.scene.frame_end = 1
#bpy.data.node_groups["Shader Nodetree"].nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.object.select_all(action='DESELECT')
# -------------------------------------


print("adding objects to blender")
#Add obejcts ----------------------------
for obj in scene.objects:

    models_path = os.getenv('CACHEPATH', '/cache')
    model = obj.mesh_id + ".fbx"
    fbxfile = os.path.join(models_path, model)

    bpy.ops.object.select_all(action='DESELECT')
    prior_objects = [object.name for object in bpy.context.scene.objects]
    bpy.ops.import_scene.fbx(filepath=fbxfile ,axis_forward='X', axis_up='Z', filter_glob="*.fbx;*.FBX")
    # try:
    # except:
    #     print(obj.mesh_id + " Failed")
    #     bpy.ops.mesh.primitive_cube_add(size=25, enter_editmode=False, location=(0, 0, 0))

    new_current_objects = [object.name for object in bpy.context.scene.objects]
    new_objects = list(set(new_current_objects)-set(prior_objects))
    
    bobj = bpy.data.objects[new_objects[0]]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    bobj.location  = [
        obj.transform.position.x,
        -obj.transform.position.y,
        obj.transform.position.z
    ]
    bobj.rotation_euler  = [
        radians(obj.transform.rotation.x),
        radians(-obj.transform.rotation.y),
        radians(-obj.transform.rotation.z)
    ]
    bobj.scale  = [
        obj.transform.scale.x,
        obj.transform.scale.y,
        obj.transform.scale.z
    ]
    bobj.animation_data_clear()

print("adding cameras to blender")
# Add cameras --------------------    
for cam in scene.cameras:   
    
    #Clean selection and get list of objects in scene
    bpy.ops.object.select_all(action='DESELECT')
    prior_objects = [object.name for object in bpy.context.scene.objects]
    
    #Create cameras
    bpy.ops.object.camera_add(
        location=(
            cam.transform.position.x,
            -cam.transform.position.y,
            cam.transform.position.z
            ),
        rotation = (
            radians(cam.transform.rotation.y + 90),
            radians(-cam.transform.rotation.x),
            radians(270 - cam.transform.rotation.z)
        )
    )
    
    #Get new camera information
    new_current_objects = [object.name for object in bpy.context.scene.objects]
    new_objects = list(set(new_current_objects)-set(prior_objects))
    current_camera = bpy.data.objects[new_objects[0]]
    
    # Apply current new camera properties
    current_camera.data.lens_unit = 'FOV'
    current_camera.data.angle = cam.FOV * 0.0174533

print("adding lights to blender")
#Add lights --------------------------
for light in scene.lights:
     #Clean selection and get list of objects in scene
    bpy.ops.object.select_all(action='DESELECT')
    prior_objects = [object.name for object in bpy.context.scene.objects]
    
    bpy.ops.object.light_add(
        type='POINT',
        radius=light.radius,
        location=(
            light.transform.position.x,
            -light.transform.position.y,
            light.transform.position.z,
            )
        )

    #Get new camera information
    new_current_objects = [object.name for object in bpy.context.scene.objects]
    new_objects = list(set(new_current_objects)-set(prior_objects))
    current_light = bpy.data.objects[new_objects[0]]
    current_light.data.energy = (light.intensity / 90) * 100#100000000 


sceneKey = bpy.data.scenes.keys()[0]
renderPath = os.getenv('RENDER_PATH', '..\..\media\camera_')
rootPath = os.path.dirname(os.path.realpath(__file__))
renderPath = os.path.join(rootPath, renderPath)
print('Looping Cameras')
c=0
for obj in bpy.data.objects:
    if(obj.type == "CAMERA"):
        print("Rendering scene["+sceneKey+"] with Camera["+obj.name+"]")
        bpy.data.scenes[sceneKey].camera = obj
        bpy.data.scenes[sceneKey].render.filepath = str(os.path.join(renderPath, str(scene.id), str(scene.id) + "_" + sceneKey + "_" + str(c)))
        bpy.ops.render.render( animation=True, use_viewport=True )
        c = c + 1
print('Done!')
# This line can be commented out if you want to check the blender result
bpy.ops.wm.quit_blender()