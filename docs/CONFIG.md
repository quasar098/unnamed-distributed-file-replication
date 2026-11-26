# client configuration file

| Option                      | Default | Description                                                                                         |
|-----------------------------|---------|-----------------------------------------------------------------------------------------------------|
| `version`                   | `1`     | Major version of the client software                                                                |
| `force_insecure_connection` | `false` | Force the usage of an unencrypted connection when communicating with nodes                          |
| `entry_endpoints`           | `[]`    | List of node endpoints that the client will attempt to connect to initial to connect to the network |

see `./example-configs/client.toml` for example

# node configuration file

| Option                      | Default    | Description                                                                                       |
|-----------------------------|------------|---------------------------------------------------------------------------------------------------|
| `version`                   | `1`        | Major version of the node software                                                                |
| `force_insecure_connection` | `false`    | Force the usage of an unencrypted connection when communicating with nodes                        |
| `host`                      | no default | The host IP address to listen on (e.g. localhost, wildcard address)                               |
| `port`                      | `33603`    | The host TCP port to listen on                                                                    |
| `storage_dir`               | no default | The relative or absolute path of the directory which stores files and other index information     |
| `http_support`              | `false`    | Respond with http `GET` requests with basic information about the node including version and name |

see `./example-configs/node.toml` for example
