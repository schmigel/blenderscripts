print('\n\n\n')
print("=============================================================")

import sys
import bpy
import json
import os.path
import requests
from dataclasses import dataclass
from math import radians
import mathutils
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

print('\nSystem argv: ')
print(sys.argv)
print('------------')

try:
    args = list(reversed(sys.argv))
    print('\nListReversed args: ')
    print(list(reversed(sys.argv)))
    params = args[1]
    params = params[params.index('=') + 1:]
    params_render360 = args[0].split()
    is360 = params_render360[0]
    is360 = int(is360[is360.index('=') + 1])
    steps = params_render360[1]
    steps = int(steps[steps.index('=') + 1])

except ValueError:
    params = []

print('------------')
print('Script params: ', params)

print('------------')
print('is360: ',is360)
print('Number of Steps: ',steps)

parser = argparse.ArgumentParser(description='Render Scene System')
args = parser.parse_args([])
print('------------')
print('args: ', args)
print('------------')

#load JSON file and get models path
print(os.path.abspath(os.path.curdir))
scene = Scene(None, [], [], [])
data = json.loads(params)
print('adding objects to blender')
print(data)
print('Setting up')

models_path = os.getenv('CACHEPATH', '/cache')
model_fname = data['_id'] + '.fbx'
model_fbx_path = os.path.join(models_path,model_fname)

#delete all objects in the scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False, confirm=False)

#setup scene
scene = bpy.context.scene
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1

#import objects
bpy.ops.import_scene.fbx(filepath=model_fbx_path, axis_forward='X', axis_up='Z',filter_glob='*.fbx;*.FBX')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
current_objects = [object.name for object in bpy.context.scene.objects]

#setup imported object
bobj = bpy.data.objects[0]
bobj.location = [0,0,0]
bobj.rotation_euler = [0,0,0]
bobj.scale = [1,1,1]
bobj.animation_data_clear()

#setup Render
scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.use_gtao = True
scene.eevee.gtao_distance = bobj.dimensions.x*2
scene.eevee.taa_render_samples = 256
scene.eevee.shadow_cascade_size = '4096'
scene.eevee.use_soft_shadows = True
scene.render.resolution_x = 1024
scene.render.resolution_y = 1024
res_x = scene.render.resolution_x
res_y = scene.render.resolution_y

#setup Bouding Box
bbox = bobj.bound_box
bbox_world = bobj.matrix_world
bbox_center_local = 0.125*sum((Vector(b) for b in bbox), Vector())
bbox_center_world = bbox_world @ bbox_center_local

#create Camera
bpy.ops.object.camera_add(enter_editmode=False, align='WORLD', location=(0, 0, 0), rotation=(0,0,0))
camera = bpy.data.objects['Camera']

#create empty object for camera track
bpy.ops.object.empty_add(type='PLAIN_AXES', location=(bbox_center_world[0],bbox_center_world[1],bbox_center_world[2]))
empty_axes = bpy.data.objects['Empty']

#parent Camera to axes and Setup
camera.parent = empty_axes
empty_axes.scale = [1,1,2.5]
if is360:
    empty_axes.rotation_euler = [radians(60),0,0]
else:
    empty_axes.rotation_euler = [radians(60),0,radians(-230)]
camera.location.z = bobj.dimensions.z

#create Plane
bpy.ops.mesh.primitive_plane_add(size=2, enter_editmode=False, location=(0, 0, 0))
plane = bpy.data.objects['Plane']
plane.scale=[1+bobj.dimensions.x*100,1+bobj.dimensions.y*100,1]
m_shadowcatcher = bpy.data.materials['m_shadowcatcher']
plane.active_material=m_shadowcatcher

#Create Light
bpy.ops.object.light_add(type='SUN', location=(0, 0, 0))
sun_light = bpy.data.objects['Sun']
sun_light.rotation_euler = [0.261799,0,0.785398]
bpy.context.object.data.energy = 10
bpy.context.object.data.shadow_cascade_max_distance = bobj.dimensions.z*10

#Render
renderPath = os.getenv('RENDER_PATH', '..\..\media\camera_')
rootPath = os.path.dirname(os.path.realpath(__file__))
renderPath = os.path.join(rootPath, renderPath)

def render():
    sceneKey = bpy.data.scenes.keys()[0]
    print('We have ' + str(len(bpy.data.objects)) + ' objects')
    print('Rendering scene[' + sceneKey + ']' + ' with Camera[' + str(camera) + ']')

    bpy.data.scenes[sceneKey].camera = camera
    bpy.data.scenes[sceneKey].render.filepath = str(
        os.path.join(renderPath, str(data['_id']), str(data['_id'])))
    bpy.ops.render.render(write_still=True)

def render360(totalsteps):
    step = 0
    sceneKey = bpy.data.scenes.keys()[0]
    bpy.data.scenes[sceneKey].camera = camera
    print('Turntable Render')
    print('We have ' + str(totalsteps) + ' steps')
    print('We have ' + str(len(bpy.data.objects)) + ' objects')
    print('Rendering scene[' + sceneKey + ']' + ' with Camera[' + str(camera) + ']')

    while step < totalsteps:
        angle_to_rotate = radians(360 / totalsteps)
        bobj.rotation_euler = [0, 0, 0 + step * angle_to_rotate]
        bpy.data.scenes[sceneKey].render.filepath = str(
            os.path.join(renderPath, str(data['_id']), str(data['_id']) + "_" +str(step+1)))
        bpy.ops.render.render(write_still=True)
        step += 1

if is360:
    render360(steps)
else:
    render()

print('-----DONE!-----')
bpy.ops.wm.quit_blender()
