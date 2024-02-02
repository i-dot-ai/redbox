module "ecs_cluster" {
 source   = "../../modules/ecs"
 cluster_name = "my-cluster"
}

module "ecs_service" {
 source           = "../../modules/ecs_service"
 service_name     = "my-service"
 cluster_id       = module.ecs_cluster.id
 task_definition_arn = module.ecs_task_definition.arn
 desired_count    = 1
}

module "ecs_task_definition" {
 source   = "../../modules/ecs_container"
 family   = "my-task-def"
 cpu      = "256"
 memory   = "512"
 containers = [
    {
      name = "my-container"
      image = "my-image"
    }
 ]
}
