import bpy

import traceback
import threading
import imp
import sys
import os

from ch_trees import parametric
from ch_trees import lsystems


def _get_tree_types():
    # Scan the the ch_trees addon folder for parameters and definitions,
    # then return two EnumProperty objects for use as the drop-down tree selector
    # (one for parametric, one for L-system)

    addon_path_parts = __file__.split(os.path.sep)[:-1]
    addon_name = addon_path_parts[-1]
    addon_path = os.path.sep.join(addon_path_parts)

    module_path_parts = [['parametric', 'tree_params'], ['lsystems', 'sys_defs']]

    # Build the drop-down menus
    enums_options = []
    for modparts in module_path_parts:
        path = os.path.join(addon_path, *modparts)
        files = [f.split('.')[0] for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

        # ex: ['ch_trees.parametric.tree_params.quaking_aspen', ...]
        modules = ['{}.{}.{}'.format(addon_name, '.'.join(modparts), f) for f in files]

        # ex: 'Quaking Aspen'
        titles = [f.replace('_', ' ').title() for f in files]

        quaking_aspen = modules[0]
        options = []
        for module, title in zip(modules, titles):
            # Use quaking aspen as the default for the drop-down
            if title == 'Quaking Aspen':
                quaking_aspen = module

            # Item format: (internal value, label, hover-text)
            options.append((module, title, title))
            
        enum_options.append(options)
    
    # Add 'Custom' menu option to parametric mode
    enum_options[0].append(('custom', 'Custom' 'Custom parameters'))
    
    return [bpy.props.EnumProperty(name="", items=tuple(opts), default=quaking_aspen) for opts in enum_options]


class TreeGen(bpy.types.Operator):
    """Generate a tree"""

    bl_idname = "object.tree_gen"
    bl_category = "TreeGen"
    bl_label = "Generate Tree"
    bl_options = {'REGISTER', 'UNDO'}

    # ---
    # Note: an empty-string 'name' parameter removes the default label from inputs

    # Item format: (internal value, label, hover-text)
    _gen_methods = (('parametric', 'Parametric', 'Parametric mode'),
                    ('lsystem', 'L-System', 'L-System mode'))
    bpy.types.Scene.tree_gen_method_input = bpy.props.EnumProperty(name="", items=_gen_methods, default='parametric')

    # Drop-downs containing tree options for each generation method
    # These are switched between by TreeGenPanel.draw() based on the state of tree_gen_method_input
    bpy.types.Scene.para_tree_type_input, bpy.types.Scene.lsys_tree_type_input = _get_tree_types()

    # Nothing exciting here. Seed, leaf toggle, and simplify geometry toggle.
    bpy.types.Scene.seed_input = bpy.props.IntProperty(name="", default=0, min=0, max=9999999)
    bpy.types.Scene.generate_leaves_input = bpy.props.BoolProperty(name="Generate leaves", default=True)
    bpy.types.Scene.simplify_geometry_input = bpy.props.BoolProperty(name="Simplify branch geometry", default=False)

    # Render inputs; auto-fill path input with user's home directory
    bpy.types.Scene.render_input = bpy.props.BoolProperty(name="Render", default=False)
    render_output_path = os.path.sep.join((os.path.expanduser('~'), 'treegen_render.png'))
    bpy.types.Scene.render_output_path_input = bpy.props.StringProperty(name="", default=render_output_path)

    self._initialize_tree_customizer_params()
    
    # ---
    def execute(self, context):
        # "Generate Tree" button callback

        thread = threading.Thread(target=self._construct, kwargs={'context': context})
        thread.start()

        return {'FINISHED'}

    # ---
    def _construct(self, context):
        # The generator's main thread.
        # Handles conditional logic for generation method selection.

        scene = context.scene
        mod_name = scene.para_tree_type_input if scene.tree_gen_method_input == 'parametric' else scene.lsys_tree_type_input
        
        if mod_name.startswith('ch_trees.parametric'):
            mod = __import__(mod_name, fromlist=[''])
            imp.reload(mod)
            parametric.gen.construct(mod.params, scene.seed_input, scene.render_input, scene.render_output_path_input, scene.generate_leaves_input)

        else:
            lsystems.gen.construct(mod_name, scene.generate_leaves_input)

        if scene.simplify_geometry_input:
            from . import utilities

            sys.stdout.write('Simplifying tree branch geometry. Blender will appear to crash; be patient.\n')
            sys.stdout.flush()

            # Catch exceptions and print them as strings
            # This will hopefully reduce random crashes
            try:
                utilities.simplify_branch_geometry(context)
            except Exception as ex:
                sys.stdout.write('\n{}\n'.format(traceback.print_exec()))
                sys.stdout.flush()

            sys.stdout.write('Geometry simplification complete\n\n')
            sys.stdout.flush()

    # ---
    def _get_params_from_customizer(self):
        tree_base_splits = scene.tree_base_splits_limit_input
        if scene.tree_base_splits_randomize_input:
           tree_base_splits *= 1

    # ---
    def _initialize_customizer_params(self):
        # Tree Shape
        tree_shape_options = (
            (0, 'Conical', 'Conical'), (1, 'Spherical', 'Spherical'), (2, 'Hemispherical', 'Hemispherical'),
            (3, 'Cylindrical', 'Cylindrical'), (4, 'Tapered Cylindrical', 'Tapered Cylindrical'),
            (5, 'Flame', 'Flame'), (6, 'Inverse Conical', 'Inverse Conical'), (7, 'Tend Flame', 'Tend Flame'),
            (8, 'Custom', 'Custom')
        )
        bpy.types.Scene.tree_shape_input = bpy.props.EnumProperty(name="", items=tree_shape_options, default=0)

        bpy.types.Scene.tree_prune_ratio_input = Float 0-1 (0)
        bpy.types.Scene.tree_prune_width_input = Float > 0 (.5)
        bpy.types.Scene.tree_prune_width_peak_input = Float >= 0 (.5)
        bpy.types.Scene.tree_prune_power_low_input = Float (0.5) <1 convex, >1 concave
        bpy.types.Scene.tree_prune_power_high_input = Float (0.5) <1 convex, >1 concave


        # Overall tree scale and scale variation
        bpy.types.Scene.g_scale_input = bpy.props.FloatProperty(name="", default=13, min=.000001, max=150)
        bpy.types.Scene.g_scale_v_input = bpy.props.FloatProperty(name="", default=3, min=0, max=149.99)

        # Level count
        bpy.types.Scene.tree_level_count_input = bpy.props.IntProperty(name="", default=3, min=1, max=6)

        # Ratio and ratio power
        bpy.types.Scene.tree_ratio_input = bpy.props.FloatProperty(name="", default=.015, min=.000001, max=1)
        bpy.types.Scene.tree_ratio_power_input = bpy.props.FloatProperty(name="", default=1.2, min=0, max=5)

        # Flare
        bpy.types.Scene.tree_flare_input = bpy.props.FloatProperty(name="", default=.6, min=0, max=10)

        # Floor split count
        bpy.types.Scene.tree_floor_split_input = bpy.props.IntProperty(name="", default=0, min=0, max=500)

        # Base split count
        bpy.types.Scene.tree_base_splits_randomize_input = bpy.props.BoolProperty(name="Randomize split count", default=False)
        bpy.types.Scene.tree_base_splits_limit_input = bpy.props.IntProperty(name="", default=0, min=0, max=10)

        # ----
        # Cumulative count of leaves and blossoms on each of the deepest level of branches
        bpy.types.Scene.tree_leaf_blos_num_input = bpy.props.IntProperty(name="", default=40, min=0, max=3000)

        # Whether or not to generate leaves
        bpy.types.Scene.tree_generate_leaves_input = bpy.props.BoolProperty(name="Generate leaves", default=True)

        # Leaf shape
        leaf_shape_options = (
         (1, 'Ovate', 'Ovate'), (2, 'Linear', 'Linear'), (3, 'Cordate', 'Cordate'), (4, 'Maple', 'Maple'),
         (5, 'Palmate', 'Palmate'), (6, 'Spiky Oak', 'Spiky Oak'), (7, 'Rounded Oak', 'Rounded Oak'),
         (8, 'Elliptic', 'Elliptic'), (9, 'Rectangle', 'Rectangle'), (10, 'Triangle', 'Triangle')
        )
        bpy.types.Scene.leaf_shape_input = bpy.props.EnumProperty(name="", items=leaf_shape_options, default=1)

        # Leaf scale
        bpy.types.Scene.tree_leaf_scale = bpy.props.FloatProperty(name="", default=.17, min=.0001, max=1000)

        # Leaf scale in x-direction
        bpy.types.Scene.tree_leaf_scale_x = bpy.props.FloatProperty(name="", default=1, min=.0001, max=1000)

        # Amount of leaf bend towards sunlight
        bpy.types.Scene.tree_leaf_bend_input = bpy.props.FloatProperty(name="", default=.6, min=0, max=1)

        # ----
        # Blossom configuration
        bpy.types.Scene.tree_generate_blossoms_input = bpy.props.BoolProperty(name="Generate blossoms", default=False)

        blossom_shape_options = ((1, 'Cherry', 'Cherry'), (2, 'Orange', 'Orange'), (3, 'Magnolia', 'Magnolia'))
        bpy.types.Scene.tree_blossom_shape_input = bpy.props.EnumProperty(name="", items=blossom_shape_options, default=1)

        # Blossom scale
        bpy.types.Scene.tree_blossom_scale_input = bpy.props.FloatProperty(name="", default=1, min=.0001, max=1000)

        # Rate at which blossoms occur relative to leaves
        bpy.types.Scene.tree_blossom_rate_input = bpy.props.FloatProperty(name="", default=0, min=0, max=1)


class TreeGenPanel(bpy.types.Panel):
    """Provides a user interface for TreeGen"""

    bl_label = "TreeGen Configuration"
    bl_idname = "OBJECT_PT_treegen"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = 'TreeGen'
    bl_context = (("objectmode"))

    # ---
    def draw(self, context):
        layout = self.layout
        scene = context.scene

        def label_row(label, prop, separator=True, one_row=False):
            # Helper method to shorten the UI code
            row = layout.row()

            if one_row or not label:
                row.prop(scene, prop)
                if label:
                    row.label(label)

            else:
                row.label(label)
                row = layout.row()
                row.prop(scene, prop)

            if separator:
                layout.separator()

        label_row('Method:', 'tree_gen_method_input')

        mode = scene.tree_gen_method_input
        label_row('Tree Type:', 'para_tree_type_input' if mode == 'parametric' else 'lsys_tree_type_input')

        if mode == 'parametric':
            label_row('Seed:', 'seed_input')

        label_row('', 'generate_leaves_input', False, True)

        label_row('', 'simplify_geometry_input', True, True)

        if mode == 'parametric':
            label_row('', 'render_input', False, True)
            if scene.render_input:
                label_row('Render output path:', 'render_output_path_input', False)
            layout.separator()

        

        # Show customizer
        if mode == 'parametric' and scene.parametric_tree_type_input == 'custom':
            # Create a new drop-down here...
            
            layout.separator()
            layout.row()
            
            # Show tree pruning configuration
            if scene.tree_shape_input == 8:
                # ...
                pass
        
        
        
        layout.separator()
        layout.row()
        layout.operator(TreeGen.bl_idname)
