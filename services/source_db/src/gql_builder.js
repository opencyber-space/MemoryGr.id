const SchemaComposer = require('graphql-compose').SchemaComposer
const SourceQuery = require('./gql_schema').SourceQuery
const SourceMutations = require('./gql_schema').SourceMutations

const schemaComposer = new SchemaComposer()

schemaComposer.Query.addFields(SourceQuery)
schemaComposer.Mutation.addFields(SourceMutations)

module.exports.builderSchema = schemaComposer.buildSchema()

