cmake_minimum_required(VERSION 3.16.3...3.19.7 FATAL_ERROR)

project(volbrain)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/niyaziacer/SlicerVolBrain")
set(EXTENSION_CATEGORY "Quantification")
set(EXTENSION_CONTRIBUTORS "Niyazi Acer (Gaziantep University)")
set(EXTENSION_DESCRIPTION "3D Slicer extension for comprehensive brain structure volume calculation and 3D visualization from volBrain segmentation outputs. Supports 108+ cortical regions, tissue classification, lobes, and macrostructures.")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/niyaziacer/SlicerVolBrain/main/Resources/Icons/SlicerVolBrain.png")
set(EXTENSION_SCREENSHOTURLS "https://raw.githubusercontent.com/niyaziacer/SlicerVolBrain/main/Screenshots/interface.png https://raw.githubusercontent.com/niyaziacer/SlicerVolBrain/main/Screenshots/3d_visualization.png")
set(EXTENSION_DEPENDS "NA") # Specified as a list or "NA" if no dependencies

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(VolBrainVolumeCalculator)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})