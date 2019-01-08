define(function (require, exports, module) {
    'use strict';

    var $ = require('jquery');
    require('node_modules/bootstrap-switch/dist/js/bootstrap-switch');

    return function (config) {
        init_switches(config);
        init_syncbutton(config);

        $('[data-toggle="tooltip"]').tooltip();

        $('i.error').tooltip({
            trigger: 'hover',
            animation: true,
            placement: 'top',
        });
    };

    function init_syncbutton(config) {
        var syncButton = $(config.sync_button);
        var syncIcon = $(syncButton.children()[0])

        syncButton.on('click', function () {
            syncButton.prop('disabled', true);
            syncIcon.addClass('fa-spin');
            $.ajax({
                url: config.sync_url,
                type: 'POST'
            })
                .done(function (data) {
                    $(config.gitlab_view).html(data);
                    init_switches(config);
                    init_syncbutton(config);
                })
                .always(function () {
                    syncButton.prop('disabled', false);
                    syncIcon.removeClass('fa-spin');
                });
        });
    }

    function init_switches(config) {
        // Initialize bootstrap switches
        var test_switch = $('input[name="test-flip"]').bootstrapSwitch();
        var doiSwitches = $('input[data-repo-id]').bootstrapSwitch();

        doiSwitches.on('switchChange.bootstrapSwitch', function (e, state) {
            // Disable the switch
            var $switch = $(e.target);
            $switch.bootstrapSwitch('disabled', true);
            var repoId = e.target.dataset.repoId;
            var method = state ? 'POST' : 'DELETE';

            $.ajax({
                url: config.hook_url,
                type: method,
                data: JSON.stringify({ id: repoId }),
                contentType: 'application/json; charset=utf-8',
                dataType: 'json'
            })
                .done(function (data, textStatus, jqXHR) {
                    var status = 'fa-exclamation text-warning';
                    if (jqXHR.status == 204 || jqXHR.status == 201) {
                        status = 'fa-check text-success';
                    }

                    // Select the correct hook status
                    var el = $('[data-repo-id="' + repoId + '"].hook-status');
                    el.addClass(status);
                    el.animate({
                        opacity: 0
                    }, 2000, function () {
                        el.removeClass(status);
                        el.css('opacity', 1);
                    });
                })
                .fail(function () {
                    // Revert back to normal
                    $switch.bootstrapSwitch('state', !state);
                })
                .always(function () {
                    // Enable the switch
                    $switch.bootstrapSwitch('disabled', false);
                });
        });
    }
});
