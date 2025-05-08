const express = require('express')
const controller = require('./controls')

const sourceRouter = express.Router()

const exec_request = async (req, resp, class_, func) => {
    const payload = req.body
    if (!payload) {
        return resp.status(500).json({
            error : true,
            message : "Invalid body"
        })
    } else {
        const classInstance = new class_()
        const result = await classInstance[func](payload)
        if (result.error) {
            return resp.status(500).json({
                error : true,
                message : result.m
            })
        }

        return resp.status(200).json({
            error : false,
            payload : result.m
        })
    }
}

//define REST Endpoints:
sourceRouter.post("/sourceExists", async (req, resp) => {
    return await exec_request(req, resp, controller.SourceController, "exists")
})

sourceRouter.post("/createNew", async (req, resp) => {
    return await exec_request(req, resp, controller.SourceController, "createNewSource")
})

sourceRouter.post("/updateSource", async (req, resp) => {
    return await exec_request(req, resp, controller.SourceController, "updateSource")
})

sourceRouter.post("/getBySourceID", async (req, resp) => {
    return await exec_request(req, resp, controller.SourceController, "getBySourceID")
})

sourceRouter.post("/getSourcesByGroup", async (req, resp) => {
    return await exec_request(req, resp, controller.SourceController, "getSourcesByGroup")
})

sourceRouter.post("/getSourcesByGroup", async (req, resp) => {
    return await exec_request(req, resp, controller.SourceController, "getSourcesByGroup")
})

sourceRouter.post("/query", async (req, resp) => {
    return await exec_request(req, resp, controller.SourceController, "query")
})

sourceRouter.post("/updateSource", async (req, resp) => {
    return await exec_request(req, resp, controller.SourceController, "updateSource")
})

sourceRouter.post("/removeBySourceID", async (req, resp) => {
    return await exec_request(req, resp, controller.SourceController, "removeBySourceID")
})

sourceRouter.post("/removeByGroupID", async (req, resp) => {
    return await exec_request(req, resp, controller.SourceController, "removeByGroupID")
})

module.exports.sourceRouter = sourceRouter
