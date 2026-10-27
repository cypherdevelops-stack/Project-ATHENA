from django.conf import settings


class AthenaDatabaseRouter:
    learning_memory_models = {
        'adaptivenewsstatistic',
        'newsamefrecord',
        'newsreactionobservation',
    }

    def database_for(self, model):
        if len(settings.DATABASES) == 1:
            return 'default'
        if model._meta.app_label == 'backtesting':
            return 'backtesting'
        if model._meta.app_label == 'news_intelligence':
            if model._meta.model_name in self.learning_memory_models:
                return 'learning_memory'
            return 'market_intelligence'
        return 'default'

    def db_for_read(self, model, **hints):
        return self.database_for(model)

    def db_for_write(self, model, **hints):
        return self.database_for(model)

    def allow_relation(self, obj1, obj2, **hints):
        return (
            obj1._state.db is None
            or obj2._state.db is None
            or obj1._state.db == obj2._state.db
        )

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if len(settings.DATABASES) == 1:
            return db == 'default'
        if db == 'default':
            return app_label not in {'backtesting'} and not (
                app_label == 'news_intelligence'
                and model_name in self.learning_memory_models
            )
        if db == 'backtesting':
            return app_label == 'backtesting'
        if db == 'market_intelligence':
            return app_label == 'news_intelligence' and model_name not in self.learning_memory_models
        if db == 'learning_memory':
            return app_label == 'news_intelligence' and model_name in self.learning_memory_models
        return False
