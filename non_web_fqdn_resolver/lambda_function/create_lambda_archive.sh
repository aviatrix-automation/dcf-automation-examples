## Shell script to install the required pip dependencies for the lambda function "example.py"
# Set up a virtual environment
virtualenv venv
source venv/bin/activate

# Install the required dependencies - requests and pydig
pip install requests
pip install pydig

# Make temp lambda_package directory
mkdir lambda_package

# Copy the function.py file to the lambda_package directory
cp function.py lambda_package

# Copy the installed packages and subdirectories to the lambda_package directory
cp -r venv/lib/python3.10/site-packages/* lambda_package

# Clean up unnecessary site-packages
rm -rf lambda_package/pip*
rm -rf lambda_package/setuptools*
rm -rf lambda_package/wheel*
rm -rf lambda_package/easy_install*
rm -rf lambda_package/__pycache__*
rm -rf lambda_package/_distutils_hack*
rm -rf lambda_package/_virtualenv*
rm -rf lambda_package/distutils-precedence.pth

# Zip the lambda_function directory
cd lambda_package
zip -r ../lambda_package.zip .

#Deactivate the virtual environment
deactivate

cd ..
# Clean up the lambda_package directory
rm -rf lambda_package

#delete the virtual environment
rm -rf venv
