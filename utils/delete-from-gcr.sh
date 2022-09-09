PROJECT_ID=worpdress-279321
#gcloud container images list-tags gcr.io/${PROJECT_ID}/${IMAGE} --filter='-tags:*' --format='get(digest)' --limit=unlimited | awk '{print "gcr.io/${PROJECT_ID}/${IMAGE}@" $1}' | xargs gcloud container images delete --quiet


gcloud container images list-tags gcr.io/${PROJECT_ID}/${IMAGE} --filter='-tags:*' --format='get(digest)' --limit=unlimited | xargs -I {arg} gcloud container images delete  "gcr.io/${PROJECT_ID}/${IMAGE}@{arg}" --quiet
