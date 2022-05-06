# Real-Time Stream Clustering Dashboard

This is how we setup the dashboard for development.
# Setup
1. First fetch textclust submodule:
    
    ```git submodule update --init --recursive```
2. Include your Twitter access-tokens in:

    ``` textclust-backend/flaskserver/twitter-access.json ```
3. Adjust your local configuration in the ```.env``` file

4. ```docker-compose build```

5. ```docker-compose up```