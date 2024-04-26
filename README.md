### System tools 

For Max
`brew install poppler`

For Ubuntu
`sudo apt-get install poppler-utils`


### Deploy to Azure functions

1: Build the Docker image locally
docker build -t myfunctionapp .

2: Push the Docker image to a container registry (Azure Container Registry in this case)

Login to Azure Container Registry (replace 'myregistry' with your registry name)
az acr login --name myregistry

Tag the image
docker tag myfunctionapp myregistry.azurecr.io/myfunctionapp:v1.0.0

Push the image
docker push myregistry.azurecr.io/myfunctionapp:v1.0.0

3: Create a new Function App in Azure (replace 'myresourcegroup', 'myplan', 'myapp', 'myregistry' with your values)
az functionapp plan create --resource-group myresourcegroup --name myplan --is-linux --sku B1
az functionapp create --resource-group myresourcegroup --name myapp --storage-account mystorageaccount --plan myplan --deployment-container-image-name myregistry.azurecr.io/myfunctionapp:v1.0.0

4: Configure the Function App to use the Docker image
az functionapp config container set --name myapp --resource-group myresourcegroup --docker-custom-image-name myregistry.azurecr.io/myfunctionapp:v1.0.0 --docker-registry-server-url https://myregistry.azurecr.io