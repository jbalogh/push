from pyramid.config import Configurator

from mozsvc.config import load_into_settings

from push.resources import Root


def main(global_config, **settings):
    config_file = global_config['__file__']
    load_into_settings(config_file, settings)

    config = Configurator(root_factory=Root, settings=settings)

    # Adds cornice.
    config.include('cornice')

    # Adds Mozilla default views.
    config.include('mozsvc')

    # Adds application-specific views.
    config.scan('push.views')

    config.add_static_view('/', 'push:static')

    return config.make_wsgi_app()
