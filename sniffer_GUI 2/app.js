'use strict';

/**
 * @ngdoc overview
 * @name customerSolutionApp
 * @description
 * # customerSolutionApp
 *
 * Main module of the application.
 */
var mapApp = angular
  .module('mapApp', [
    'ngResource',
    'ngRoute'
  ])
  .config(['$routeProvider', function ($routeProvider) {
    $routeProvider.
      when('/', {
        templateUrl: 'views/networkmap.tpl.html',
        controller: 'NetworkMapController'
      }).
      otherwise({
        redirectTo: '/'
      });
  }
]);

//manual bootstrap for less angular magic
angular.element(document).ready(function () {
  angular.bootstrap(document, ['mapApp']);
});