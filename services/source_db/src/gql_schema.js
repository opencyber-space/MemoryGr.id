const { Component } = require('./schema');

const SourceTC = require('./schema').SourceTC

const SourceQuery = {
    sourceById: SourceTC.mongooseResolvers.findById({
        lean: true
    }),
    sourceByIds: SourceTC.mongooseResolvers.findByIds({
        lean: true
    }),
    sourceOne: SourceTC.mongooseResolvers.findOne({
        lean: true
    }),
    sourceMany: SourceTC.mongooseResolvers.findMany({
        lean: true
    }),
    sourceCount: SourceTC.mongooseResolvers.count({
        lean: true
    }),
    sourceConnection: SourceTC.mongooseResolvers.connection({
        lean: true
    }),
    sourcePagination: SourceTC.mongooseResolvers.pagination({
        lean: true
    }),
};

const SourceMutations = {
    /*
        Writes are not supported with GraphQL for components registry,
        This is a future work
    */  
}
module.exports.SourceQuery = SourceQuery
module.exports.SourceMutations = SourceMutations
