import subprocess

left,top = 55, 475
right,bottom = 1020, 1440
N = 9
cell_size = int((right-left)/float(N)+1) #186
height = (bottom - top)
width = (right - left)
gap = 1 #(width % cell_size)/(width/cell_size - 1)

def getScreenshot():
  subprocess.call(["adb", "shell", "screencap", "-p", "/sdcard/screen.png"])
  subprocess.call(["adb", "pull", "/sdcard/screen.png"])
  #subprocess.call(["adb", "shell", "screencap", "-p", "/sdcard/screen.png"])

def gotoNext():
  subprocess.call(['adb', 'shell', 'input', 'tap', '1000', '1500'])

def rotate(location, direction):
  start = map(int,(
    left + cell_size * (location[1] + .5),
    top + cell_size * (location[0] + .5)))
  end = (
    start[0] + direction[1] * cell_size,
    start[1] + direction[0] * cell_size
  )

  subprocess.call(map(str,['adb', 'shell', 'input', 'swipe', start[0], start[1], end[0], end[1],
  "10"]))

def getField():
  getScreenshot()
  from PIL import Image
  im = Image.open("screen.png")
  field = im.crop((left,top,right,bottom))
  field.save("field.png")
  return field

def generateTiles():
  # Appears to now work for all board sizes

  field = getField()
  pix=field.load()
  n = 0
  x = 0
  # diagonal until we hit a block
  while field.getpixel((x,x)) == (255,255,255,255):
    pix[x,x]=(0,0,0,255)
    x += 1
  # hop into the block some
  n = x*3

  # find the left wall
  x=0
  while field.getpixel((x,n)) == (255,255,255,255):
    pix[x,n]=(0,0,0,255)
    x += 1
  left = x

  # find the right wall
  while field.getpixel((x,n)) != (255,255,255,255):
    pix[x,n]=(0,255,0,255)
    x += 1

  global cell_size
  cell_size = x - left

  # find the next left wall
  while field.getpixel((x,n)) == (255,255,255,255):
    pix[x,n]=(0,0,255,255)
    x += 1

  global gap
  gap = x-cell_size-left

  global N

  field.save("field.png")

  N = int(field.size[0]/cell_size)
  print "N:", N
  print "gap:", gap
  print "cell size:", cell_size

  tiles = []
  tile_size = cell_size + gap
  for y in range(0, height, tile_size):
    row = []
    tiles.append(row)
    for x in range(0, width, tile_size):
      tile = field.crop((x, y, x+cell_size, y+cell_size))
      tile.save("%s-%s.png" % (y/tile_size, x/tile_size))
      row.append(tile)
  return tiles

def buildMap():
  def getColor(pixel):
    #       R    G    B    A
    blue=   58, 129, 189, 255
    orange=255, 146,  58, 255
    purple=230,  73, 197, 255
    green=  99, 227,  90, 255
    high_diff = 100000
    high_color = 0
    for c in [orange, blue, green, purple]:
      diff = sum(
        map(
          lambda (a,b):(a-b)**2,
          zip(c, pixel)))
      if diff < high_diff:
        high_diff = diff
        high_color = c
    if high_color == orange:
      return 0
    elif high_color == blue:
      return 3
    elif high_color == green:
      return 1
    return 4

  tiles = generateTiles()
  world = []
  center = cell_size / 2
  colorpx_y = cell_size/3 # 45
  tid = 0
  for row in tiles:
    world_row = []
    world.append(world_row)
    for tile in row:
      # scan from the center outwards until you hit non-white
      cx = center
      cy = center
      r = 0
      up = True
      down = True
      left = True
      right = True
      pix = tile.load()
      while True in (up, down, left, right):
        if up == True: up = tile.getpixel((cx, cy-r)) == (255,255,255,255)
        if down == True: down = tile.getpixel((cx, cy+r)) == (255,255,255,255)
        if left == True: left = tile.getpixel((cx-r, cy)) == (255,255,255,255)
        if right == True: right = tile.getpixel((cx+r, cy)) == (255,255,255,255)
        if up == False: up = r
        if down == False: down = r
        if left == False: left = r
        if right == False: right = r

        if up == True:
          pix[cx,cy-r]=(255,0,0,255)
        if down == True:
          pix[cx,cy+r]=(255,0,0,255)
        if left == True:
          pix[cx-r,cy]=(255,0,0,255)
        if right == True:
          pix[cx+r,cy]=(255,0,0,255)

        r += 1

      tile.save("%s-%s.png" % ( tid / N, tid % N))
      tid += 1

      color = getColor(tile.getpixel((cx, cy-r-2)))

      if color == 3: # X's are blue
        char = 'X'
      elif up+down+left+right == 0:
        char = 'O'
      else:
        m = max((up,down,left,right))
        if m == up:
          char = '^'
        elif m == down:
          char = 'v'
        elif m == left:
          char = '<'
        elif m == right:
          char = '>'
        else:
          char = "?"

      print "\033[0;" + str(31 +color%10 ) +"m",
      print "%s" %char,
      #print ":", char, up, down, left, right, color

      world_row.append((char, color))
    print "\033[0;0m"
  return world

def solve_path(world):
  # find start/end
  end = None
  start = None
  for row_num, row in enumerate(world):
    for col_num, cell in enumerate(row):
      if cell[1] == 4: # purple
        if cell[0] == 'O':
          end = (row_num, col_num)
        else:
          start = (row_num, col_num)

  print start, '-->', end


  def at(row, col):
    print "at:",row,col
    if row <0 or col < 0 or row >= N or col >= N:
      return ('X', 3)
    return world[row][col]

  def cost(ndir, nval):
    #ndir = (drow, dcol)
    #nval = arrow neighbor has
    cost = {(0,1):{'>':2, '<':0},
            (1,0):{'v':2, '^':0}}
    if ndir in cost:
      if nval in cost[ndir]:
        return cost[ndir][nval]
    else:
      ndir = -1*ndir[0], -1*ndir[1]
      if nval in cost[ndir]:
        return 2-cost[ndir][nval]
    return 1

  def check((dist, pos, _), direction):
    nrow = pos[0] + direction[0]
    ncol = pos[1] + direction[1]
    down = at(nrow, ncol)
    if down[0] in "XO":
      return

    c = cost(direction, down[0])
    search.put((dist + c, (nrow, ncol), direction))


  # bfs
  from Queue import PriorityQueue as Queue

  best = {}
  search = Queue()
  search.put((0, end, None))
  while not search.empty():
    node = search.get()
    if node[1] in best: # we've already found a better solution
      continue
    best[node[1]] = node
    pos = node[1]

    cell = world[pos[0]][pos[1]]
    if cell[1] == 4 and cell[0] != 'O':
      break
    check(node, (1,0))
    check(node, (0,1))
    check(node, (0,-1))
    check(node, (-1,0))
  print "--"
  for k in sorted(best.keys()):
    print k, best[k]
  path = []
  cur = start
  while cur != end:
    path.append(cur)
    choice = best[tuple(cur)]
    r,c = cur
    r -= choice[2][0]
    c -= choice[2][1]
    cur = (r,c)
  path.append(cur)
  return path

def solve():
  world = buildMap()
  path = solve_path(world)

  def performMove(start, end):
    cell = world[start[0]][start[1]]

    neededDir = end[0]-start[0], end[1]-start[1]
    curDir = {'^':(-1,0), 'v':(1,0), '<':(0,-1), '>':(0,1)}[cell[0]]

    if curDir == neededDir:
      return

    # if it needs 2 turns, rotate to some middle direction
    if curDir[0]*-1 == neededDir[0] and curDir[1]*-1 == neededDir[1]:
      rotate(start, (neededDir[1],neededDir[0]))
    rotate(start, neededDir)

  move_start = path[0]
  for move_next in path[1:]:
    performMove(move_start, move_next)
    move_start= move_next
  print world[path[0][0]][path[0][1]]


import time
while True:
  solve()
  time.sleep(.5)
  #gotoNext()
  #time.sleep(1)

print 'done'



























