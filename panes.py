"""
A 'pane' is a simple kind of 2D scene graph.  A pane is 
a graphics context with its own origin and scale factors, 
both relative to its parent frame.  A pane may contain 
individual graphics objects (polygons and polylines) and 
nested panes, each in coordinates relative to the pane.

We use pygame as the underlying graphics system. As a 
consequence of this, we have double-buffering and need 
to explicitly render and flip to see the scene. 
"""
import pygame

SIZE = 500,500
screen = None
pygame.init()
pygame.font.init()

class Error(Exception):
    """Base class for exceptions in this module"""
    pass

class PanesError(Error):
    """Not further differentiated"""

    def __init__(self, expression, message):
        self.expression = expression;
        self.message = message

class Pane:
    """
    A graphics context and a list of objects to be rendered in 
    that context. 
    """
    def __init__(self, parent=None, root=False,  tr=(0,0),
                     sf=None, sfx=None, sfy=None):
        if not root and not parent:
            raise PanesError("Every non-root pane must have a parent")
        self.parent = parent
        self.dx, self.dy = tr
        self.sfx = sfx or sf or 1.0
        self.sfy = sfy or sf or 1.0
        self.contents = [ ]

        global screen
        if root:
            if not screen:
                screen = pygame.display.set_mode(SIZE)
                screen.fill((255,255,255))
                self.width, self.height = SIZE
        else:
            parent.append(self)
            self.width = self.sfx * parent.width
            self.height = self.sfy * parent.height

        # We need to track extent (width and height) because
        # some scaling operations, particularly for grid layouts,
        # may be sensitive to the available extent.  Width and
        # height are scaled to the units of the current pane.

    def append(self, el):
        """
        Append a polyline, polygon, or nested pane. 
        """
        self.contents.append(el)

    def render(self, transform=None):
        transform = Transform(self.dx, self.dy,
                                  self.sfx, self.sfy, prior=transform) 
        for el in self.contents:
            el.render(transform)
        if not self.parent:
            pygame.display.flip()
            screen.fill((255,255,255)) # For next frame

    # Sometimes we want to translate a coordinate from one frame into another.
    # For example, if we put a frame around a pane, we may want the x or y
    # coordinate of the pane in the context of the surrounding frame. Typically
    # we will want only the x or the y coordinate, so we provide those
    # independently. Currently we support transformation only into an
    # ancestor pane. 

    def x_out(self, x, ancestor):
        """
        x coordinate in the parent pane
        """
        pane = self
        while pane != ancestor:
            x = (x * pane.sfx) + pane.dx
            if not pane.parent:
                raise PanesError("ancestor not on path to root")
            pane = pane.parent
        return x

    def y_out(self, y, ancestor):
        """
        y coordinate in the parent pane
        """
        pane = self
        while pane != ancestor:
            y = (y * pane.sfy) + pane.dy
            if not pane.parent:
                raise PanesError("ancestor not on path to root")
            pane = pane.parent
        return y
    


class GridPane(Pane):
    """
    Scale to overlay the parent pane with an X*Y grid, i.e., Y coordinate
    becomes "row" and X coordinate becomes "column".  
    """
    def __init__(self, parent, rows, columns):
        if not parent:
            raise PanesError("A GridPane may not be the root pane")
        self.parent = parent
        self.dx, self.dy = 0,0
        self.sfx = (parent.width) / columns
        self.sfy = (parent.height) / rows
        self.contents = [ ]
        self.width = columns
        self.height = rows
        parent.append(self)

class Framed(Pane):
    """
    A pane with the same scale as the parent, but with margins carved out 
    on top, bottom, left, right
    """
    def __init__(self, parent, left=0, right=0, top=0, bottom=0):
        if not parent:
            raise PanesError("A Framed pane may not be the root pane")
        self.parent = parent
        self.dx = left
        self.dy = top
        self.sfx = 1.0
        self.sfy = 1.0
        self.contents = [ ]
        self.width = parent.width - (left + right)
        self.height = parent.height - (top + bottom)
        parent.append(self)

class Transform:
    """
    A transform relates world coordinates to screen coordinates.
    We build up transforms as we traverse a tree of Panes. 

    Attributes: 
       dx, dy:  Origin relative to screen
       sf:      Scale factor
    """
    def __init__(self,  dx, dy, sfx, sfy,  prior=None):
        if prior:
            self.dx = prior.dx + prior.sfx*dx
            self.dy = prior.dy + prior.sfy*dy
            self.sfx = prior.sfx * sfx
            self.sfy = prior.sfy * sfy
        else:
            self.dx = dx
            self.dy = dy
            self.sfx = sfx
            self.sfy = sfy

    def tx(self, pt):
        x,y = pt
        return self.dx + self.sfx * x, self.dy + self.sfy * y



#  Often we want a pane scaled to some real-world coordinate system.
#  For example, we might want the X dimension to cover Monday-Friday
#  with some room at the left for labels  (so 0=Monday, 1=Tuesday, etc),
#  while the Y dimension we might want 8am-7pm (scale in hours) with
#  some space at the top for labels and a small margin at the bottom.
#  This does not require a new class of object, but only some convenience
#  functions for producing Panes with the appropriate transformations.



def is_numeric(x):
    return isinstance(x,int) or isinstance(x,float)

class Poly:
    """
    Base class for polylines and polygons. 
    Sequence of points, relative to a Pane. 
    """
    def __init__(self, points=[], stroke=None, fill=None):
        self.__validate_points(points)
        self.points = points

    def _validate_points(self, points):
        for point in points:
            if len(point) != 2:
                raise PanesError("Each point must be a pair of numbers")
            x,y = point
            if not is_numeric(x) or not is_numeric(y):
                raise PanesError("Points must be pairs of int or float")
            

class Polygon(Poly):
    """
    A polygon is closed and may have a fill.
    """
    def __init__(self, points=[], stroke=None, fill=None):
        self._validate_points(points)
        self.points = points
        self.stroke = stroke or 0
        self.fill = fill or (255,0,0)
            

    def render(self, context):
        """
        Render this polygon in the given 
        relative to the transformation context
        """
        assert isinstance(context, Transform)
        screen_coords = [ ]
        for pt in self.points:
            screen_coords.append( context.tx(pt) )
        pygame.draw.polygon(screen, self.fill, screen_coords, self.stroke)

        
class GridCellPoly(Polygon):
    """
    A rectangular polygon whose corners are the 
    boundaries of a row and column in a GridPane.  
    (Note (row,col) order is transposed from (x,y) ) 
    """
    def __init__(self, row, col, stroke=None, fill=None):
        super().__init__([(col,row), (col, row+1),
                          (col+1,row+1), (col+1,row),
                          (col, row)],
                         stroke, fill)

class Text:
    """
    A string of text at coordinates (x,y)
    """
    def __init__(self, text, x, y, size=12, color=(0,0,0)):
        self.loc = (x,y)
        # print("Placing text at {},{}".format(x,y))
        self.text = text
        self.color=color
        self.size = size

    def render(self, context):
        assert isinstance(context, Transform)
        font = pygame.font.SysFont("Helvetica", self.size)
        screen_coords = context.tx(self.loc)
        # print(screen_coords) # Debugging
        img = font.render(self.text, True, self.color)
        screen.blit(img,screen_coords)

    
if __name__ == "__main__":
    root = Pane(root=True)

    p1 = Polygon([(0,0), (0,100), (100,100), (0,0)])
    root.append(p1)

    child = Pane(parent=root, sf=.5, tr=(100,100))
    child.append(Polygon([(0,0), (0,100), (100,100), (100,0), (0,0)],
                             fill=(0,255,0)))

    
    grandchild = Pane(parent=child, sf=0.5, tr=(100,100))
    grandchild.append(p1)


    root.render()
    input("Press enter to end")    
    

    
