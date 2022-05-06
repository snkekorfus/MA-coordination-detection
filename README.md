# Coordination detection with **textClust**

This repository contains the code for the master thesis "Detecting coordinated user groups through textual stream clustering".
The main contribution is the new package *coordination_detection*.
With this package the coordination between users can be calculated based on similarity.
Therefore, different data acquistion methods and similarity calculation methods are offered.
This package is also incorporated into the **textClust** dashboard with an additional component for the dashboard.
Thus, this repository also offers an extension to the **textClust** dashboard.
Since this dashboard is used in the second phase of the two-phase framework of [1], it can also be seen as an extension of this study.

In the folder *notebooks* different jupyter notebooks are stored.
They were either used to create additional material for the thesis or to experiment during the development of the pipeline that created coordination-aware community graphs.
In each of the notebooks a short description explains what it does.

The *data* folder that contains the tweets used for this master thesis in a MongoDB database was removed from this repository to not violate any privacy policies.
The dataset can be downloaded from [here](https://uni-muenster.sciebo.de/s/sNdCjC4uErSlhwr).
The password must be requested from the author (snke@tutanota.de).
To make use of the data, it must be put in the folder *textclust* and renamed to data.
Afterwards it is used as a volume by docker.
For analysis purposes make sure that the field ANALYSIS in the .env file is set to True.
This avoids the start of a new clustering run after the docker containers got started.

For the swift case the cluster with the id 34859 was used at the timestamp 2022-02-25 14:07:13 in the cluster session 8273444c-abdd-4410-829a-970846ebd00e.
The Myanmar case used the cluster 14 at the timestamp 2022-02-21 13:01:16 from the clustering session 8c280348-74c0-4f64-8a77-ec8dc2fd2cc5.

### Sources

[1] Assenmacher, D., Clever, L., Pohl, J. S., Trautmann, H., & Grimme, C. (2020). A two-phase framework for detecting manipulation campaigns in social media. In Lecture Notes in Computer Science (including subseries Lecture Notes in Artificial Intelligence and Lecture Notes in Bioinformatics): Vol. 12194 LNCS. Springer International Publishing. https://doi.org/10.1007/978-3-030-49570-1_14