# Description of de:NBI portal compute center format

## project / group

A project has many characteristics.

###  Members

Elixir user who are assigned to the project.

```
"denbiProjectMembers" : [
         {
            "id" : <ELIXIR-ID>
            "login-namespace:elixir" : "<ELIXIR USER NAME>"
            "login-namespace:elixir-persistent" : "UNIQUE ELIXIR USER ID",
            "preferredMail" : "<ELIXIR USER MAIL>"
         },
         ...
      ],
```

### Resources

Resources available to the project.

#### Cores
Number of (virtual) cores which can be used by instances.
```
"denbiCoresLimit" : <INT>
```
#### Number of instances
Number of instances which can be spawned.
```
"denbiProjectNumberOfVms" : <INT>
```
#### Object Storage
Amount of object storage measured in GB the project can use.
```
"denbiProjectObjectStorage" : <INT (GB)>
```
_This resource property is not yet considered._

#### RAM 
Amount of RAM in MB that can be used.
```
"denbiRAMLimit" : <INT (MB)>
```

#### Volumes

Count of volumes and the maximum available storage in GB capacity over 
all volumes.

```
"denbiVolumeCounter" : <INT>,
"denbiVolumeLimit" : <INT (GB)>
```

#### Flavors

```  
"denbiOpenStackFlavors" : {
         "de.NBI medium" : "3"
      },
```

_This resource property is not yet considered._