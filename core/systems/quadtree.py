import pygame

class Quadtree:
    def __init__(self, bounds, capacity=8):
        """
        bounds: pygame.Rect representing the area this quadtree covers.
        capacity: Maximum number of objects per node before splitting.
        """
        self.bounds = bounds
        self.capacity = capacity
        self.entities = []
        self.divided = False
        self.northeast = None
        self.northwest = None
        self.southeast = None
        self.southwest = None

    def insert(self, entity):
        """
        Inserts an entity into the quadtree. The entity must have a .rect attribute.
        """
        if not hasattr(entity, 'rect') or not self.bounds.colliderect(entity.rect):
            return False

        if len(self.entities) < self.capacity:
            self.entities.append(entity)
            return True
        else:
            if not self.divided:
                self.subdivide()

            # Try to insert into children
            if self.northeast.insert(entity): return True
            if self.northwest.insert(entity): return True
            if self.southeast.insert(entity): return True
            if self.southwest.insert(entity): return True
            
            # If the entity overlaps boundaries and fits in none of the children strictly,
            # keep it in the parent node.
            self.entities.append(entity)
            return True

    def subdivide(self):
        x = self.bounds.x
        y = self.bounds.y
        w = self.bounds.width / 2
        h = self.bounds.height / 2

        self.northwest = Quadtree(pygame.Rect(x, y, w, h), self.capacity)
        self.northeast = Quadtree(pygame.Rect(x + w, y, w, h), self.capacity)
        self.southwest = Quadtree(pygame.Rect(x, y + h, w, h), self.capacity)
        self.southeast = Quadtree(pygame.Rect(x + w, y + h, w, h), self.capacity)
        self.divided = True

    def query(self, range_rect, found=None):
        """
        Returns a list of entities that collide with range_rect.
        """
        if found is None:
            found = []

        if not self.bounds.colliderect(range_rect):
            return found

        # Check objects at this level
        for entity in self.entities:
            if range_rect.colliderect(entity.rect):
                found.append(entity)

        # Check children
        if self.divided:
            self.northwest.query(range_rect, found)
            self.northeast.query(range_rect, found)
            self.southwest.query(range_rect, found)
            self.southeast.query(range_rect, found)

        return found

    def clear(self):
        """
        Clears the quadtree recursively.
        """
        self.entities = []
        self.divided = False
        self.northeast = None
        self.northwest = None
        self.southeast = None
        self.southwest = None