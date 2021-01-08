

module.exports = {
    webpack: (config, options) => {
        config.resolve.modules.push(
            __dirname, "src"
        )
        console.log(config.resolve.modules)
        return config
    }
}

