# Application icon

`icon.png` is the editor's 512×512 application icon. The editor supplies 16, 24,
32, 48, 64, 128 and 256 pixel versions to Tk for the main window and subsequent
dialogs. The path is relative to `scenario_editor.py`, so launching from another
working directory works as well.

`icon.ico` contains those seven sizes for Windows shortcuts or future packaging.
To rebuild it with ImageMagick:

```sh
magick assets/app/icon.png -define icon:auto-resize=256,128,64,48,32,24,16 assets/app/icon.ico
```

The original artwork was generated with the built-in image generation tool,
then resized for the application. Final generation prompt:

> Use case: logo-brand. Asset: one finished square desktop app icon for a WWII hex-map scenario editor. A large golden-outlined olive-green hexagonal tile, a bold ivory WWII tank silhouette in its center (side view, barrel facing left), and a chunky small golden-yellow drawing pencil diagonally over the lower-right corner. Tank and pencil must be instantly recognizable at 32 pixels. Simple crisp flat-color graphic with thick shapes and strong contrast, minimal detail and absolutely no textures. Clean solid fills, olive #4b5728 tile, warm ivory tank, gold pencil and border, charcoal #252923 background filling the ENTIRE square canvas, including outside the hexagon. This is an OPAQUE square icon. No transparency, holes, mottling, camouflage patches, gradients, light effects, cast shadows, frame, text, insignia, flags or letters. Center the composition with 5% charcoal margin around all edges. One icon only.
