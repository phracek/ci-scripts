add_tag_result = {
    "spec": {
        "tags": [
            {
                "name": "1-el8",
                "annotations": {
                    "openshift.io/display-name": "Test 1 (RHEL 8)",
                    "openshift.io/provider-display-name": "Red Hat, Inc.",
                    "description": "test description",
                    "iconClass": "icon-test",
                    "tags": "test,test",
                    "version": "1",
                },
                "from": {
                    "kind": "DockerImage",
                    "name": "registry.redhat.io/rhel8/test-1:latest",
                },
                "referencePolicy": {"type": "Local"},
            }
        ]
    }
}

add_tag_latest_result = {
    "spec": {
        "tags": [
            {
                "name": "latest",
                "annotations": {
                    "openshift.io/display-name": "Test 1 (Latest)",
                    "openshift.io/provider-display-name": "Red Hat, Inc.",
                    "description": "test description\n\nWARNING: By selecting this tag,"
                    " your application will automatically update"
                    " to use the latest version available on OpenShift,"
                    " including major version updates.\n",
                    "iconClass": "icon-test",
                    "tags": "test,test",
                    "version": "1",
                },
                "from": {"kind": "ImageStreamTag", "name": "1-el8"},
                "referencePolicy": {"type": "Local"},
            }
        ]
    }
}

add_tag_custom_result = {
    "spec": {
        "tags": [
            {
                "name": "some custom name",
                "annotations": {
                    "openshift.io/display-name": "Test 13 (RHEL 8)",
                    "openshift.io/provider-display-name": "Red Hat, Inc.",
                    "description": "test description",
                    "iconClass": "icon-test",
                    "tags": "test,test",
                    "version": "13",
                },
                "from": {
                    "kind": "DockerImage",
                    "name": "registry.redhat.io/rhel8/test-13:latest",
                },
                "referencePolicy": {"type": "Local"},
            }
        ]
    }
}

create_annotation_result = {
    "openshift.io/display-name": "Test 1 (RHEL 8)",
    "openshift.io/provider-display-name": "Red Hat, Inc.",
    "description": "test description",
    "iconClass": "icon-test",
    "tags": "test,test",
    "version": "1",
}

create_annotation_latest_result = {
    "openshift.io/display-name": "Test 1 (Latest)",
    "openshift.io/provider-display-name": "Red Hat, Inc.",
    "description": (
        "test description\n\nWARNING: By selecting this tag,"
        " your application will automatically update to use "
        "the latest version available on OpenShift, including major version updates.\n"
    ),
    "iconClass": "icon-test",
    "tags": "test,test",
    "version": "1",
}

create_header_result = {
    "kind": "ImageStream",
    "apiVersion": "image.openshift.io/v1",
    "metadata": {"name": "test", "annotations": {"openshift.io/display-name": "Test"}},
    "spec": {"tags": []},
}

description_msg = (
    "test description\n\n"
    "WARNING: By selecting this tag, your application will automatically"
    " update to use the latest version available on OpenShift, including major version updates.\n"
)

generate_json_result = {
    "kind": "ImageStream",
    "apiVersion": "image.openshift.io/v1",
    "metadata": {"name": "test", "annotations": {"openshift.io/display-name": "Test"}},
    "spec": {
        "tags": [
            {
                "name": "1-el8",
                "annotations": {
                    "openshift.io/display-name": "Test 1 (RHEL 8)",
                    "openshift.io/provider-display-name": "Red Hat, Inc.",
                    "description": "test description",
                    "iconClass": "icon-test",
                    "tags": "test,test",
                    "version": "1",
                },
                "from": {
                    "kind": "DockerImage",
                    "name": "registry.redhat.io/rhel8/test-1:latest",
                },
                "referencePolicy": {"type": "Local"},
            },
            {
                "name": "latest",
                "annotations": {
                    "openshift.io/display-name": "Test 1 (Latest)",
                    "openshift.io/provider-display-name": "Red Hat, Inc.",
                    "description": f"{description_msg}",
                    "iconClass": "icon-test",
                    "tags": "test,test",
                    "version": "1",
                },
                "from": {"kind": "ImageStreamTag", "name": "1-el8"},
                "referencePolicy": {"type": "Local"},
            },
        ]
    },
}
