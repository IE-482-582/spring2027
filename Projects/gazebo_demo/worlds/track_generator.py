from PIL import Image, ImageDraw

# Output file
OUT = "running_track_8192x4096.png"

# Image size
W, H = 8192, 4096

# Real-world dimensions (meters)
TRACK_LEN = 176.91
TRACK_HGT = 92.52

# Scale (pixels per meter)
SCALE = min(W / TRACK_LEN, H / TRACK_HGT)

def m(px): return px * SCALE

# Track parameters (meters)
LANE_W = 1.22
LANES = 8
INNER_R = 36.5
STRAIGHT = 84.39

# Convert to pixels
inner_r = m(INNER_R)
lane_w = m(LANE_W)
straight = m(STRAIGHT)

cx, cy = W // 2, H // 2

# Create image
img = Image.new("RGB", (W, H), (60, 120, 60))  # grass
draw = ImageDraw.Draw(img)

# Draw track (filled)
for i in range(LANES):
    r_outer = inner_r + lane_w * (i + 1)

    # Arcs
    left = [cx - straight/2 - r_outer, cy - r_outer,
            cx - straight/2 + r_outer, cy + r_outer]
    right = [cx + straight/2 - r_outer, cy - r_outer,
             cx + straight/2 + r_outer, cy + r_outer]

    draw.pieslice(left, 90, 270, fill=(180, 50, 40))
    draw.pieslice(right, -90, 90, fill=(180, 50, 40))

    # Straights
    draw.rectangle([cx - straight/2, cy - r_outer,
                    cx + straight/2, cy + r_outer],
                   fill=(180, 50, 40))

# Lane lines
for i in range(1, LANES):
    r = inner_r + lane_w * i

    left = [cx - straight/2 - r, cy - r,
            cx - straight/2 + r, cy + r]
    right = [cx + straight/2 - r, cy - r,
             cx + straight/2 + r, cy + r]

    draw.arc(left, 90, 270, fill=(255, 255, 255), width=4)
    draw.arc(right, -90, 90, fill=(255, 255, 255), width=4)

    draw.line([(cx - straight/2, cy - r),
               (cx + straight/2, cy - r)],
              fill=(255, 255, 255), width=4)

    draw.line([(cx - straight/2, cy + r),
               (cx + straight/2, cy + r)],
              fill=(255, 255, 255), width=4)

img.save(OUT)
print("Saved:", OUT)
