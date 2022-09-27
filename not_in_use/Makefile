BRANCH_NAME := $(BRANCH_NAME)
PROJECT_ID :=  worpdress-279321

.PHONY: all

all: end2end_tests

frontend:

unittests_frontend: frontend

backend:

unittests_backend: backend



frontend_with_tests: unittests_frontend

backend_with_tests: unittests_frontend

end2end_tests: frontend_with_tests backend_with_tests




clean:
	echo NOOP
