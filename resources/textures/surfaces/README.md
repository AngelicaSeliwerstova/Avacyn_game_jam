# Hospital surface swatches

Original procedural RGB textures for the hospital, authored in this repository.
No external images are used. Each surface has 128 and 256 pixel variants.

Rebuild with:

```powershell
.\.venv\Scripts\python.exe tools/create_hospital_surfaces.py
```

Paint, enamel and ceramic have restrained surface variation; oak has continuous
grain; vinyl, linen and curtains have separate patterns. Worn textiles use the
same scale with darker fibres and stains. Periodic patterns repeat without board
or panel outlines being baked into medical equipment or bedding.

Material repeats are defined in `config/settings.py`. Hospital role assignments
and world variants live in `game/levels/hospital_finishes.py`.
