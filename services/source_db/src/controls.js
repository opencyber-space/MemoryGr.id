const schemas = require('./schema')

class SourceController {
    async exists(sourceID) {
        try {
            const result = await schemas.Source.findOne({
                "sourceID": sourceID
            })
            if (!result) {
                throw `SourceID ${sourceID} does not exist`
            }
            return { error: false, m: result }
        } catch (err) {
            return { error: true, m: err }
        }
    }

    async createNewSource(payload) {
        try {

            const sourceID = payload.sourceID
            if (!sourceID) {
                throw `SourceID key not found`
            }

            // check if it exists:
            const exist = await this.exists(sourceID)
            if (!exist.error) {
                throw `SourceID ${sourceID} not found`
            }

            // create a new source
            const source = new schemas.Source(payload)
            const result = await source.save()
            if (!result) {
                throw `Failed to create source entry ${sourceID}`
            }

            return { error: false, m: result }

        } catch (err) {
            return { error: true, m: err }
        }
    }

    async updateSource(payload) {
        const sourceID = payload.sourceID
        const updatePayload = payload.data

        try {
            if (!sourceID || !updatePayload) {
                throw "sourceID or data fields not found"
            }

            // check if source exists:
            const exists = await this.exists(sourceID)
            if (exists.error) {
                throw `sourceID ${sourceID} not found`
            }

            // perform update:
            updatePayload.sourceID = sourceID
            const updateResult = await schemas.Source.updateOne(
                { "sourceID": sourceID }, updatePayload
            )

            if (!updateResult) {
                throw `Failed to update ${sourceID}`
            }

            return {error: false, m: updateResult}
        } catch (err) {
            return { error: true, m: err }
        }
    }

    async getBySourceID(payload) {
        try {

            const sourceID = payload.sourceID
            if (!sourceID) {
                throw "sourceID key not found"
            }

            const result = await schemas.Source.find({"sourceID": sourceID})
            return {error: false, m : result}
        } catch(err) {
            return {error: true, m : err}
        }
    }

    async getSourcesByGroup(payload) {
        try {

            const groupID = payload.groupID
            if (!groupID) {
                throw "groupID key not found"
            }

            const result = await schemas.Source.find({"groupID": groupID})
            return {error: false, m : result}
        } catch(err) {
            return {error: true, m : err}
        }
    }

    async query(payload) {
        try {

            const query = payload.query
            if (!query) {
                throw "query key not found"
            }

            const result = await schemas.Source.find(query)
            return {error: false, m : result}
        } catch(err) {
            return {error: true, m : err}
        }
    }

    async removeBySourceID(payload) {
        try {

            const sourceID = payload.sourceID
            if (!sourceID) {
                throw "sourceID key not found"
            }

            const result = await schemas.Source.deleteMany({"sourceID": sourceID})
            return {error: false, m : result}
        } catch(err) {
            return {error: true, m : err}
        }
    }

    async removeByGroupID(payload) {
        try {

            const groupID = payload.groupID
            if (!groupID) {
                throw "groupID key not found"
            }

            const result = await schemas.Source.deleteMany({"groupID": groupID})
            return {error: false, m : result}
        } catch(err) {
            return {error: true, m : err}
        }
    }
}

module.exports.SourceController = SourceController