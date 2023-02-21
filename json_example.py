json = {
  "$id": "https://example.com/person.schema.json",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "description": "Data package with station details to be send to the 3D-Configurator",
  "title": "StationConfiguration",
  "type": "SmartMobilityHub",
  "stationName": "TestStation",
  "linkedTo": "Bahnhof Eisleben",
  "planned_modules": {
    "base": {
      "quantity": "1"
    },
    "lastName": {
      "type": "string",
      "description": "The person's last name."
    },
    "age": {
      "description": "Age in years which must be equal to or greater than zero.",
      "type": "integer",
      "minimum": 0
    }
  },

  "catalogue":
    {
      "base": {

      }
    }
}