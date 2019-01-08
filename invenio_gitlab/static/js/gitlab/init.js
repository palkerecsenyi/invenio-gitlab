require([
    'jquery',
    'node_modules/bootstrap-switch/dist/js/bootstrap-switch',
    'js/gitlab/view'
], function () {
    /*
     * It preloads js/github/view to give it a name so you're free to use it
     * from any places.
     */
    console.info("js/gitlab/init is loaded");
});
