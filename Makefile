.PHONY: run_daily_tests shellcheck build_images

run_daily_tests:
	bash daily_tests/daily_scl_tests.sh

shellcheck:
	./run-shellcheck.sh `git ls-files *.sh`

build_images:
	podman build -t quay.io/sclorg/upstream-daily-tests:0.10.0 -f Dockerfile.daily-tests .
