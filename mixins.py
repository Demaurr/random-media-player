class ResetMixin:
    def reset(self, exclude=None, deep=False):
        """
        Reset object to default state.
        
        :param exclude: list of attributes to skip
        :param deep: reset nested ResettableMixin objects
        """
        exclude = set(exclude or [])

        defaults = self._get_defaults()

        for key in list(self.__dict__.keys()):
            if key in exclude:
                continue

            if key in defaults:
                setattr(self, key, defaults[key])
            else:
                delattr(self, key)

        for key, value in defaults.items():
            if key not in self.__dict__:
                setattr(self, key, value)

        if deep:
            for value in self.__dict__.values():
                if isinstance(value, ResetMixin):
                    value.reset(deep=True)

    def _get_defaults(self):
        """
        Override this in child classes.
        Should return a dict of default values.
        """
        return {}