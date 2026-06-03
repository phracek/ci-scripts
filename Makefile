.PHONY: run_daily_tests shellcheck build_images daily_tests eol_checker

run_daily_tests:
	bash daily_tests/daily_scl_tests.sh

shellcheck:
	./run-shellcheck.sh `git ls-files *.sh`

build_images: daily_tests eol_checker

daily_tests:
	podman build -t quay.io/sclorg/upstream-daily-tests:0.10.5 -f Dockerfile.daily-tests .

eol_checker:
	podman build -t quay.io/sclorg/upstream-eol-checker:0.10.5 -f Dockerfile.eol-checker .
