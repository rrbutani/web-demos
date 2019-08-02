workflow "Check, test, and build the web-demos" {
  on = "push"
  resolves = [
    "Build the base image",
    "Build Stage",
    "Check Stage",
    "Check Scripts",
    "Test Stage",
    "Upload Coverage",

    # "Package Stage",
    # "Build Regular Dist Container",
    "Upload Regular Dist Container",

    # "Debug Package Stage",
    # "Build Debug Dist Container",
    "Upload Debug Dist Container",
  ]
}

# workflow "Does a release!" {
#   on = "push"
#   resolves = [
#     # , "Build the base image"
#     # , "Build Stage"
#     # , "Check Stage"
#     # , "Check Scripts"
#     # , "Test Stage"
#     # , "Package Stage"
#     # , "Upload Coverage"
#     # , "Build Regular Dist Container"
#     # , "Debug Package Stage"
#     # , "Build Debug Dist Container"
#     "Upload Regular Dist Container",
#     "Upload Debug Dist Container",
#   # , "Upload Regular Wheel"
#   # , "Upload Debug Wheel"
#   ]
# }

action "Log into Docker Hub" {
  uses = "actions/docker/login@8cdf801b322af5f369e00d85e9cf3a7122f49108"
  secrets = ["DOCKER_USERNAME", "DOCKER_PASSWORD"]
}

action "Build the base image" {
  uses = "actions/docker/cli@86ff551d26008267bb89ac11198ba7f1d807b699"
  args = "build --target base -t web-demos:base -f Dockerfile ."
}

action "Build Stage" {
  uses = "actions/docker/cli@86ff551d26008267bb89ac11198ba7f1d807b699"
  needs = ["Build the base image"]
  args = "build --target build -t web-demos:build -f Dockerfile ."
}

action "Check Stage" {
  uses = "actions/docker/cli@86ff551d26008267bb89ac11198ba7f1d807b699"
  needs = ["Build Stage"]
  args = "build --target check -t web-demos:check -f Dockerfile ."
}

action "Check Scripts" {
  uses = "docker://web-demos:build"
  needs = ["Build Stage"]
  args = "in-proj pipenv run check-scripts"
}

action "Test Stage" {
  uses = "actions/docker/cli@86ff551d26008267bb89ac11198ba7f1d807b699"
  needs = ["Check Stage"]
  args = "build --target test -t web-demos:test -f Dockerfile ."
}

action "Package Stage" {
  uses = "actions/docker/cli@86ff551d26008267bb89ac11198ba7f1d807b699"
  needs = ["Test Stage"]
  args = "build --target package -t web-demos:package -f Dockerfile ."
}

action "Upload Coverage" {
  uses = "docker://web-demos:test"
  needs = ["Test Stage"]
  args = "in-proj pipenv run upload-cov"
  env = {
    "COVERALLS_SERVICE_NAME" = "github-actions"
  }
  secrets = ["COVERALLS_REPO_TOKEN", "CODECOV_TOKEN"]

  # workflow "Does a release!" {
  #   on = "push"
  #   resolves = [
  #     # , "Build the base image"
  #     # , "Build Stage"
  #     # , "Check Stage"
  #     # , "Check Scripts"
  #     # , "Test Stage"
  #     # , "Package Stage"
  #     # , "Upload Coverage"
  #     # , "Build Regular Dist Container"
  #     # , "Debug Package Stage"
  #     # , "Build Debug Dist Container"
  #     "Upload Regular Dist Container",
  #     "Upload Debug Dist Container",
  #   # , "Upload Regular Wheel"
  #   # , "Upload Debug Wheel"
  #   ]
  # }
}

# # action "Upload Regular Wheel" {
# #   uses = "UPL_CONTAINER"
# #   needs = ["Package Stage"]
# #   args = "build --build-arg BASE_IMAGE=web-demos:package --build-arg TAG=${GITHUB_REF} --build-arg FILE='dist/dist/*.whl'"
# #   # secrets = [ "GITHUB_TOKEN" ]
# #   env = { "DEBUG" = "False" }
# # }

action "Build Regular Dist Container" {
  uses = "actions/docker/cli@86ff551d26008267bb89ac11198ba7f1d807b699"
  needs = ["Package Stage"]
  args = "build --build-arg COMMIT_SHA=${GITHUB_SHA} --target dist -t web-demos:dist -f Dockerfile ."
}

action "Tag Regular Dist Container" {
  uses = "actions/docker/tag@8cdf801b322af5f369e00d85e9cf3a7122f49108"
  needs = ["Build Regular Dist Container"]
  args = "web-demos:dist rrbutani/web-demos"
}

action "Tag Regular Dist Container With Version" {
  uses = "docker://rrbutani/docker-version-tag"
  needs = ["Build Regular Dist Container"]
  args = "web-demos:dist rrbutani/web-demos Dockerfile"
}

action "Upload Regular Dist Container" {
  uses = "actions/docker/cli@86ff551d26008267bb89ac11198ba7f1d807b699"
  needs = [
    "Log into Docker Hub",
    "Tag Regular Dist Container",
    "Tag Regular Dist Container With Version",
  ]
  args = "push rrbutani/web-demos"
}

action "Build the base debug image" {
  uses = "actions/docker/cli@86ff551d26008267bb89ac11198ba7f1d807b699"
  needs = ["Test Stage"]
  args = "build --build-arg DEBUG=true -t web-demos:base-debug -f Dockerfile ."
}

action "Debug Package Stage" {
  uses = "actions/docker/cli@86ff551d26008267bb89ac11198ba7f1d807b699"
  needs = ["Build the base debug image"]
  args = "build --build-arg DEBUG=true --target package -t web-demos:package-debug -f Dockerfile ."
}

# # action "Upload Debug Wheel" {
# #   uses = "UPL_CONTAINER"
# #   needs = ["DEBUG Package Stage"]
# #   args = "build --build-arg BASE_IMAGE=web-demos:package-debug --build-arg TAG=${GITHUB_REF} --build-arg FILE='dist/dist/*.whl'"
# #   # secrets = [ "GITHUB_TOKEN" ]
# #   env = { "DEBUG" = "False" }
# # }

action "Build Debug Dist Container" {
  uses = "actions/docker/cli@86ff551d26008267bb89ac11198ba7f1d807b699"
  needs = ["Debug Package Stage"]
  args = "build --build-arg DEBUG=true --build-arg COMMIT_SHA=${GITHUB_SHA} --target dist -t web-demos:dist-debug -f Dockerfile ."
}

action "Tag Debug Dist Container" {
  uses = "actions/docker/tag@8cdf801b322af5f369e00d85e9cf3a7122f49108"
  needs = ["Build Debug Dist Container"]
  args = "web-demos:dist-debug rrbutani/web-demos-debug"
}

action "Tag Debug Dist Container With Version" {
  uses = "docker://rrbutani/docker-version-tag"
  needs = ["Build Debug Dist Container"]
  args = "web-demos:dist-debug web-demos-debug Dockerfile"
}

action "Upload Debug Dist Container" {
  uses = "actions/docker/cli@86ff551d26008267bb89ac11198ba7f1d807b699"
  needs = [
    "Log into Docker Hub",
    "Tag Debug Dist Container",
    "Tag Debug Dist Container With Version",
  ]
  args = "push rrbutani/web-demos-debug"
}
