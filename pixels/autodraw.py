import logging
import coloredlogs
import math
import template_manager
import asyncio
from PIL import Image

logger = logging.getLogger(__name__)

coloredlogs.install(level='DEBUG', logger=logger)

RGB_LENIENCE = 30

class AutoDrawer():
    def __init__(self, client, image, startX, startY, is_animated=False): # image can also be a directory
        self.client = client
        self.image = image
        self.startX = startX
        self.startY = startY
        self.is_animated = is_animated

    def rgbToHex(self, rgb):
        return '%02x%02x%02x' % rgb

    def calculateCooldownPeriod(self, endpoint):
        requests_reset = self.client.RateLimiters[endpoint].requests_reset
        requests_remaining = self.client.RateLimiters[endpoint].requests_remaining
        if (requests_reset is not None) and (requests_remaining is not None):
            if (math.ceil(float(requests_reset != 0))) and (int(requests_remaining) != 0):
                cooldown_period = math.ceil(float(requests_reset)) / int(requests_remaining)
                return cooldown_period
        return None

    def isCycleCurrent(self):
        _, changed = template_manager.get_template_for(self.image).get_current_frame_path()
        return not changed

    async def getPixels(self):
        current_pixels = await self.client.get_pixels()
        height, width = await self.client.get_size()

        canvas = Image.frombytes('RGB', (width, height), current_pixels)

        return canvas

    async def shouldChangePixel(self, current_pixel, pixel):
        if abs(current_pixel[0] - pixel[0]) >= RGB_LENIENCE:
            if abs(current_pixel[1] - pixel[1]) >= RGB_LENIENCE:
                if abs(current_pixel[2] - pixel[2]) >= RGB_LENIENCE:
                    return True
        return False 

    async def getCoordsToDraw(self, image):
        current_pixels = await self.getPixels()

        coords = []
        for x in range(0, image.width):
            for y in range(0, image.width):
                current_pixel = current_pixels.getpixel((x + self.startX, y + self.startY))
                image_pixel = image.getpixel((x, y))

                # We don't need to change the pixel if it's close enough to what it should be
                if await self.shouldChangePixel(current_pixel, image_pixel):
                    coords.append((x + self.startX, y + self.startY))

        return coords

    async def setPixel(self, coords, rgb):
        await self.client.set_pixel(coords, rgb)
        cooldown_period = self.calculateCooldownPeriod('/set_pixel')
        if cooldown_period is not None:
            await asyncio.sleep(cooldown_period)

    async def draw(self, is_guarded=True):
        while True:
            # Get our image
            if self.is_animated:
                image = Image.open(template_manager.get_template_for(self.image).get_current_frame_path()[0]).convert('RGBA')
            else:
                image = Image.open(self.image).convert('RGBA')

            """
            Here's how this process works:
            
            We are in a while True loop, which is used for animated images as well as guarding. We get the latest image in the animation if it's animated,
            otherwise we just load the non-animated image. Then, we calculate the difference on the canvas versus our image and return a set of coordinates.
            With those coordinates, we add a pixel with the proper color at that position. If we're not animated or guarded, we break the while loop after
            that's done.

            """

            # Check which pixels are not valid
            pixels = await self.getCoordsToDraw(image)

            total_pixels = image.height * image.width
            logger.info(f"{total_pixels - len(pixels)}/{total_pixels} are valid") # TODO: update comment on how it works, fix draw check and make priorities
  
            for coords in pixels:
                # Check if our cycle is outdated
                if self.is_animated:
                    if not self.isCycleCurrent():
                        logger.info('Starting next animation cycle')
                        break

                # logger.warning(f"pixel at {coords} was changed. current: {current_pixels.getpixel(coords)[0:3]}, previous: {pixel_cache[coords]}")
                current_pixels = await self.getPixels()
                current_pixel = current_pixels.getpixel((coords))

                pixel = image.getpixel((coords[0] - self.startX, coords[1] - self.startY))


                if await self.shouldChangePixel(current_pixel, pixel):
                    await self.setPixel(coords, self.rgbToHex(pixel[0:3]))

            if not self.is_animated and not is_guarded:
                return
                