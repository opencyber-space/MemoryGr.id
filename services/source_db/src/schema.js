const mongoose = require('mongoose')
const gqlComposer = require('graphql-compose-mongoose')


const offlineVideo = new mongoose.Schema({
    container: {type: String, required: true},
    storageVideoPath: {type: String, required: true},
    videoParameters: mongoose.Schema({
        codec: {type: String, required: true},
        fps: {type: Number, required: true},
        bitrate: {type: Number, required: false}
    }),
    geoJson: {type: mongoose.SchemaTypes.Mixed, required: false, default: {}}
})

const liveVideo = new mongoose.Schema({
    protocol: {type: String, required: true},
    streamURL: {type: String, required: true},
    onvifURL: {type: String, required: true},
    onvifAuthInfo: {type: mongoose.SchemaTypes.Mixed, required: false, default: {}},
    isOnvifAuth: {type: Boolean, required: true},
    streamParameters: mongoose.Schema({
        codec: {type: String, required: true},
        fps: {type: Number, required: true},
        bitrate: {type: Number, required: false}
    }),
    geoJson: {type: mongoose.SchemaTypes.Mixed, required: false, default: {}}
})


const sourcesSchema = new mongoose.Schema({
    sourceID: {type: String, required: true},
    groupID: {type: String, required: true},
    label: {type: String, required: true},
    description: {type: String, required: false},
    sourceType: {type: String, required: true},
    liveSourceInfo: {type: liveVideo, required: false},
    offlineVideo: {type: offlineVideo, required: false},
    sourceMetadata: mongoose.Schema({
        frameProperties: mongoose.Schema({
            width: {type: Number, required: true},
            height: {type: Number, required: true},
            encodingFormat: {type: String, required: false}
        }),
        calibrationData: {type: mongoose.SchemaTypes.Mixed, required: false, default: {}},
    }),
    alerts: {type: mongoose.SchemaTypes.Mixed, required: false, default: {}}
})

const Source = mongoose.model("Source", sourcesSchema)

module.exports.Source = Source
module.exports.SourceTC = gqlComposer.composeMongoose(Source)