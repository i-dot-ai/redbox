# `Settings`

Redbox used the `pydantic_settings` library to manage settings. This library allows for settings to be defined in a type-safe way using Pydantic models. This is done by creating a `Settings` class that inherits from `BaseSettings` and defines the settings as class attributes.

::: redbox.models.settings.Settings

# Elasticsearch Settings

Depending on the deployment scenarios we have two different ways to configure Elasticsearch: `ElasticLocalSettings` and `ElasticCloudSettings`.

## `ElasticLocalSettings`

::: redbox.models.settings.ElasticLocalSettings

## `ElasticCloudSettings`

::: redbox.models.settings.ElasticCloudSettings