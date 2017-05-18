python scalability_couchbase.py > scalability_couchbase.json
python scalability_vpc.py > scalability_vpc.json 
python scalability_top.py > scalability_top.json 

./aws.sh scalability_couchbase.json $S3_BUCKET_NAME $AWS_ACCESS_KEY_ID $AWS_SECRET_ACCESS_KEY
./aws.sh scalability_vpc.json $S3_BUCKET_NAME $AWS_ACCESS_KEY_ID $AWS_SECRET_ACCESS_KEY
./aws.sh scalability_top.json $S3_BUCKET_NAME $AWS_ACCESS_KEY_ID $AWS_SECRET_ACCESS_KEY
