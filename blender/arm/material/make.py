import bpy
import arm.utils
import arm.nodes
import arm.material.make_shader as make_shader
import arm.material.mat_batch as mat_batch
import arm.material.mat_state as mat_state
import arm.material.make_texture as make_texture

def glsltype(t): # Merge with cycles
    if t == 'RGB' or t == 'RGBA' or t == 'VECTOR':
        return 'vec3'
    else:
        return 'float'

def glslvalue(val):
    if str(type(val)) == "<class 'bpy_prop_array'>":
        res = []
        for v in val:
            res.append(v)
        return res
    else:
        return val

def parse(material, mat_data, mat_users, mat_armusers, rid):
    wrd = bpy.data.worlds['Arm']

    # No batch - shader data per material
    if not wrd.arm_batch_materials or material.name.startswith('armdefault'):
        rpasses, shader_data, shader_data_name, bind_constants, bind_textures = make_shader.build(material, mat_users, mat_armusers, rid)
    else:
        rpasses, shader_data, shader_data_name, bind_constants, bind_textures = mat_batch.get(material)

    # Material
    for rp in rpasses:

        c = {}
        c['name'] = rp
        c['bind_constants'] = [] + bind_constants[rp]
        c['bind_textures'] = [] + bind_textures[rp]
        mat_data['contexts'].append(c)

        if rp == 'mesh':
            const = {}
            const['name'] = 'receiveShadow'
            const['bool'] = material.receive_shadow
            c['bind_constants'].append(const)

            if bpy.data.cameras[0].rp_sss_state == 'On':
                sss_node = arm.nodes.get_node_by_type(material.node_tree, 'SUBSURFACE_SCATTERING')
                if sss_node != None and sss_node.outputs[0].is_linked: # Check linked node
                    const = {}
                    const['name'] = 'materialID'
                    const['int'] = 2
                    c['bind_constants'].append(const)

            # TODO: Mesh only material batching
            if wrd.arm_batch_materials:
                # Set textures uniforms
                if len(c['bind_textures']) > 0:
                    c['bind_textures'] = []
                    for node in material.node_tree.nodes:
                        if node.type == 'TEX_IMAGE':
                            tex_name = arm.utils.safesrc(node.name)
                            tex = make_texture.make(node, tex_name)
                            if tex == None: # Empty texture
                                tex = {}
                                tex['name'] = tex_name
                                tex['file'] = ''
                            c['bind_textures'].append(tex)

                # Set marked inputs as uniforms
                for node in material.node_tree.nodes:
                    for inp in node.inputs:
                        if inp.is_uniform:
                            uname = arm.utils.safesrc(inp.node.name) + arm.utils.safesrc(inp.name)  # Merge with cycles
                            const = {}
                            const['name'] = uname
                            const[glsltype(inp.type)] = glslvalue(inp.default_value)
                            c['bind_constants'].append(const)

        elif rp == 'translucent':
            const = {}
            const['name'] = 'receiveShadow'
            const['bool'] = material.receive_shadow
            c['bind_constants'].append(const)
    
    mat_data['shader'] = shader_data_name + '/' + shader_data_name

    return shader_data.sd, rpasses
