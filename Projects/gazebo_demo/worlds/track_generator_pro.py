from PIL import Image, ImageDraw, ImageFont
import math

OUT = "running_track_stagger_correct.png"

W, H = 8192, 4096

TRACK_LEN = 176.91
TRACK_HGT = 92.52

SCALE = min(W / TRACK_LEN, H / TRACK_HGT)
def m(x): return x * SCALE

LANE_W = 1.22
LANES = 8
INNER_R = 36.5
STRAIGHT = 84.39

cx, cy = W // 2, H // 2
inner_r = m(INNER_R)
lane_w = m(LANE_W)
straight = m(STRAIGHT)

TRACK = (180, 50, 40)
LINE = (255, 255, 255)
GRASS = (60, 120, 60)

img = Image.new("RGB", (W, H), GRASS)
draw = ImageDraw.Draw(img)

# ---- TRACK ----
for i in range(LANES):
    r_outer = inner_r + lane_w * (i + 1)

    left = [cx - straight/2 - r_outer, cy - r_outer,
            cx - straight/2 + r_outer, cy + r_outer]
    right = [cx + straight/2 - r_outer, cy - r_outer,
             cx + straight/2 + r_outer, cy + r_outer]

    draw.pieslice(left, 90, 270, fill=TRACK)
    draw.pieslice(right, -90, 90, fill=TRACK)

    draw.rectangle([cx - straight/2, cy - r_outer,
                    cx + straight/2, cy + r_outer],
                   fill=TRACK)

# ---- STRAIGHT PORTION ----
draw.rectangle([W/2, 0, 
				W, LANES*lane_w], 
				fill=TRACK)
			
# ---- SRAIGHT LINES ----
for i in range(LANES):
	y = lane_w * i
    
	draw.line([(W/2, y),
			   (W,   y)], fill=LINE, width=4)
               				
# ---- LANE LINES ----
for i in range(1, LANES):
    r = inner_r + lane_w * i

    left = [cx - straight/2 - r, cy - r,
            cx - straight/2 + r, cy + r]
    right = [cx + straight/2 - r, cy - r,
             cx + straight/2 + r, cy + r]

    draw.arc(left, 90, 270, fill=LINE, width=4)
    draw.arc(right, -90, 90, fill=LINE, width=4)

    draw.line([(cx - straight/2, cy - r),
               (cx + straight/2, cy - r)], fill=LINE, width=4)
    draw.line([(cx - straight/2, cy + r),
               (cx + straight/2, cy + r)], fill=LINE, width=4)

'''
# ---- CORRECT STAGGERED STARTS (parallel, no fan) ----

start_ref_x = cx + straight/2 - m(2)  # right edge reference

for i in range(LANES):
    lane_center_y = cy - inner_r + lane_w*(i + 0.5)

    # correct stagger distance (meters)
    lane_r = INNER_R + LANE_W * (i + 0.5)
    stagger_m = math.pi * (lane_r - INNER_R)

    x = start_ref_x - m(stagger_m)

    # draw horizontal line
    draw.line([
        (x, lane_center_y),
        (x - m(20), lane_center_y)
    ], fill=(255,255,0), width=4)
'''

# ---- LANE NUMBERS (aligned with stagger) ----
try:
    font = ImageFont.truetype("DejaVuSans-Bold.ttf", int(m(1.5)))
except:
    font = None

for i in range(6):
    lane_r = inner_r + lane_w*(i + 3.35)

    x = cx + straight/2 - m(10)*1.5
    y = cy - lane_r

    txt = Image.new("RGBA", (200,200), (0,0,0,0))
    td = ImageDraw.Draw(txt)
    td.text((100,100), str(i+1), fill=LINE, font=font, anchor="mm")

    txt = txt.rotate(90, expand=1)
    img.paste(txt, (int(x), int(y)), txt)

for i in range(6):
    lane_r = inner_r + lane_w*(i - 0.5)

    x = cx + straight/2 - m(10)*i
    y = cy + lane_r

    txt = Image.new("RGBA", (200,200), (0,0,0,0))
    td = ImageDraw.Draw(txt)
    td.text((100,100), str(i+1), fill=LINE, font=font, anchor="mm")

    txt = txt.rotate(270, expand=1)
    img.paste(txt, (int(x), int(y)), txt)
    
img.save(OUT)
print("Saved:", OUT)
