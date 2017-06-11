#These commands create a virtual environment 
#with paramiko and cryptography for our lambda
#function. For now this is not automated.
#Read this blog post for more:

#http://websitenotebook.blogspot.com/2017/05/creating-paramiko-and-cryptography.html

#NOTE: This most easily works with Python 2.7 which is 
#supported both by Lambda and EC2 instances for reasons 
#explained in the related blog posts.

#update the ec2 isntance
sudo yum update -y

#see what versions of python are available
#sudo yum list | grep python3

#install the one we want
#sudo yum install python35.x86_64 -y

sudo pip install virtualenv --upgrade

#switch to temp directory
cd /tmp

#create virtual environment
virtualenv -p /usr/bin/python2.7 python27

#activate virtual environment
source python35/bin/activate

#install dependencies
sudo yum install gcc -y
sudo yum install python35-devel.x86_64 -y
sudo yum install openssl-devel.x86_64 -y
sudo yum install libffi-devel.x86_64 -y

#upgrade pip
pip install --upgrade pip

#install cryptography and parmaiko paramiko
pip install paramiko

#create zip file
cd python27/lib/python2.7/site-packages

#and...how was I supposed to know this?
#http://stackoverflow.com/questions/38963857/import-error-from-cyptography-hazmat-bindings-constant-time-import-lib
#use . to get hidden directories not *
zip -r9 /tmp/lambda.zip . -x \*__pycache__\*

cd ../../..

cd lib64/python2.7/site-packages

zip -g -r9 /tmp/lambda.zip . -x \*__pycache__\*

deactivate

#run this from local machine to copy down the zip we just created
#scp username@ipaddress:pathtofile localsystempath
#change the key and IP address below
scp -i "[yourkey].pem" ec2-user@[ip-address]:/tmp/lambda.zip lambda.zip
