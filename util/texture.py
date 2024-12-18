import OpenGL.GL as gl
import pygame


class Texture:
    def __init__(self, image_path):
        # Load image using pygame
        self.texture_id = gl.glGenTextures(1)
        image = pygame.image.load(image_path).convert_alpha()

        # Flip the image vertically
        image = pygame.transform.flip(image, False, True)

        image_data = pygame.image.tostring(image, "RGBA", 1)
        width, height = image.get_size()

        # Bind and configure OpenGL texture
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexImage2D(
            gl.GL_TEXTURE_2D,
            0,
            gl.GL_RGBA,
            width,
            height,
            0,
            gl.GL_RGBA,
            gl.GL_UNSIGNED_BYTE,
            image_data,
        )

        self.width, self.height = width, height

    def bind(self):
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)

    def get_size(self):
        return self.width, self.height


textures = {}


def get_texture_cached(name) -> Texture:
    image_path = f"assets/{name}.png"
    if image_path not in textures:
        textures[image_path] = Texture(image_path)
    return textures[image_path]
