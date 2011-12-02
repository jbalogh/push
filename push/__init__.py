from pyramid.config import Configurator

from mozsvc.config import load_into_settings

from push import storage
from push.resources import Root


def loader(config, settings, section):
    """Instantiate the class in settings with the keyword arguments.

    The following lines are identical:
        >>> loader(.., {'backend': 'x.y.Class', 'flag': 3}, ..)
        >>> x.y.Class(flag=3)
    """
    kwargs = settings['config'].get_map(section)
    cls = config.maybe_dotted(kwargs.pop('backend'))
    return cls(**kwargs)


def main(global_config, **settings):
    config_file = global_config['__file__']
    load_into_settings(config_file, settings)

    config = Configurator(root_factory=Root, settings=settings)

    config.registry['queuey'] = loader(config, settings, 'queuey')
    config.registry['storage'] = loader(config, settings, 'storage')

    # Adds cornice.
    config.include('cornice')

    # Adds Mozilla default views.
    config.include('mozsvc')

    # Adds application-specific views.
    config.scan('push.views')

    config.add_static_view('/', 'push:static')

    return config.make_wsgi_app()
