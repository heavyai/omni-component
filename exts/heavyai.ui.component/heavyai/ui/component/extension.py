from __future__ import annotations
import asyncio
import contextlib
from typing import Dict, Optional, TYPE_CHECKING

import omni.kit.app

if TYPE_CHECKING:
    import omni.ui as ui


class Component:
    """
    The base class that UI elements should be subclassed from

    Attributes
    ----------
    name : Optional[str]
        The name of the root container.
    style : Optional[Dict]
        The local style of the root container.
    height : Optional[int]
        The height of the root container.
    width : Optional[int]
        The width of the root container
    style_type_name_override : Optional[str]
        By default, we use typeName to look up the style.
        But sometimes it's necessary to use a custom name.
        For example, when a widget as a part of another widget.(Label is a part of Button)
        This property can override the name to use in style.
    """
    style: Optional[Dict] = None
    height: Optional[int] = None
    width: Optional[int] = None
    name: Optional[str] = None
    style_type_name_override: Optional[str] = None

    def __init__(self, render_on_init=True, **kwargs):
        """
        Parameters
        ----------
        render_on_init : bool
            If the render method should be called upon component creation
        """
        # ui.Container is ui.VStack/HStack/ZStack/etc
        self._root: ui.Container = None
        self._debounce_task: asyncio.Future = None

        props = self.get_props()  # grab declared component props

        for k, v in kwargs.items():
            try:
                assert k in props    # ensure the prop has been declared
                setattr(self, k, v)  # set props
            except AssertionError:
                raise AssertionError(f"Prop '{k}' must be annotated") from None

        # in rare situations you may need to choose when the component initially renders
        if render_on_init:
            self.render()

    @classmethod
    def get_props(cls):
        d = {}
        for c in cls.mro():
            try:
                d.update(**c.__annotations__)
            except AttributeError:
                pass
        return d

    @property
    def visible(self):
        if self._root:
            return self._root.visible
        return False

    @visible.setter
    def visible(self, new_visible):
        if not self._root:
            raise Exception("Component has not been rendered") from None
        self._root.visible = new_visible

    @property
    def enabled(self):
        if self._root:
            return self._root.enabled

    @enabled.setter
    def enabled(self, value):
        if self._root:
            self._root.enabled = value

    def get_root(self, Container: ui.Container, default_visible=True, **kwargs):
        """
        Creates and returns a new container upon initial call.

        Clears the container and returns reference upon subsequent calls.
        This allows a component to be re-rendered without losing its positioning
        """
        if self._root:
            self._root.clear()
        else:
            if self.height is not None:
                kwargs.update(height=self.height)
            if self.width is not None:
                kwargs.update(width=self.width)
            if self.style is not None:
                kwargs.update(style=self.style)
            if self.name is not None:
                kwargs.update(name=self.name)
            if self.style_type_name_override is not None:
                kwargs.update(style_type_name_override=self.style_type_name_override)
            self._root = Container(**kwargs)
            self._root.visible = default_visible
        return self._root

    async def render_async(self):
        """Waits for next frame before re-rendering"""
        await omni.kit.app.get_app().next_update_async()
        self.render()

    def update(self, loop=asyncio.get_event_loop()):
        """Used to re-render the component"""
        asyncio.ensure_future(self.render_async(), loop=loop)

    def update_debounce(self, delay=0.2):
        """
        Queues re-render after a delay and resets the timer on subsequent calls if timer has not completed
        """
        async def run_after_delay():
            await asyncio.sleep(delay)
            await self.render_async()

        with contextlib.suppress(Exception):
            self._debounce_task.cancel()

        self._debounce_task = asyncio.ensure_future(run_after_delay())

    def render(self):
        raise NotImplementedError()

    def __del__(self):
        """
        Note: `__del__` is not reliably called when parent component is destroyed or re-rendered

        If a component requires clean-up (such as subscriptions, windows, frames, or event listeners),
        the parent component/class must manually call destroy when appropriate.
        """
        self.destroy()

    def destroy(self):
        """
        If a component requires clean-up (such as subscriptions, windows, frames, or event listeners),
        the parent component/class must manually call destroy when appropriate.
        """
        pass
