'use strict';

mapApp.controller('NetworkMapController', ['$scope', '$rootScope', '$timeout', function ($scope, $rootScope, $timeout) {

  var width = 800,
    height = 600,
    container;

//  var color = d3.scale.ordinal()
//    .domain([0,1,2])
//    .range(["#2FB4E9","#C4014B","#F4A100"]);

  var color = function (value) {
    //return "#4EA500"; //green
    if ((parseInt(value)) < 186) {
      return "#4EA500"; //green
    }
    else if ((parseInt(value)) < 371){
      return "#FDD805"; //yellow
      //return "#A0A0A0"; //GREY
    }
    else if ((parseInt(value)) > 371) {
      return "#ED1C24"; //red
    }
    else {
      //return "#FDD805"; //yellow
      return "#A0A0A0"; //GREY      
    }
  };

  var radius = function(value){
    if (value === "Coordinator") {
      return 22;
    }
    else if (value === "Router") {
      return 19;
    }
    else if (value === "End Device") {
      return 16;
    }
    else if(value === "Disconnected"){
      return 19;
    }
  }

  var letter = function (value) {
    if (value === "Coordinator") {
      return "C";
    }
    else if (value === "Router") {
      return "R";
    }
    else if (value === "End Device") {
      return "E";
    }
    else if (value === "Disconnected") {
      return "D";
    }
  };

  var click = function (d, doSelection, that) {
    if (doSelection) {
      d3.selectAll('.selectify').style('opacity', 0);

      d3.select(that).select('.selectify')
        .style('opacity', .5)
        .style('stroke-opacity', 1);
    }

    $rootScope.$broadcast("NODE_CLICKED_EVENT", d);
  };

  function refreshData() {
    d3.select("svg")
      .remove();

    var force = d3.layout.force()
      .size([width, height])
      .charge(-800)
      .friction(0.50)
      .linkStrength(1)
      .gravity(.10)
      .linkDistance(40);

    var zoom = d3.behavior.zoom()
      .scaleExtent([.5, 10])
      .on("zoom", zoomed);

    var svg = d3.select("#networkMap").append("svg")
      .attr("width", width)
      .attr("height", height)
      .call(zoom);

    container = svg.append("g");

    d3.json("/data/network.json" + '?nocache=' + (new Date()).getTime(), function (error, graph) {

      var nodes = graph.nodes.slice(),
        links = [],
        bilinks = [];

      nodes = graph.nodes.slice(),
        links = [],
        bilinks = [];

      nodes.forEach(function(node){
        if(node.deviceType === "Coordinator"){
          $timeout(function () {
            click(node, false);
          }, 100);
        }
      });

      graph.links.forEach(function (link) {

        //replace ieee_address & parent_ieee_address with source & target, because that's what d3 wants

        if (link.ieee_address !== undefined) {
          Object.defineProperty(link, "source",
            Object.getOwnPropertyDescriptor(link, "ieee_address"));
          delete link["ieee_address"];
        }

        if (link.parent_ieee_address !== undefined) {
          Object.defineProperty(link, "target",
            Object.getOwnPropertyDescriptor(link, "parent_ieee_address"));
          delete link["parent_ieee_address"];
        }

        var result = [];
        nodes.forEach(function (node) {
          if (node.ieee_address === link.source) result.push(node);
        });
        var s = result ? result[0] : undefined;

        var result = [];
        nodes.forEach(function (node) {
          if (node.ieee_address === link.target) result.push(node);
        });
        var t = result ? result[0] : undefined;

        var i = link; // intermediate node
        nodes.push(i);
        links.push({source: s, target: i}, {source: i, target: t});
        bilinks.push([s, i, t]);
      });

      svg.append("svg:defs").selectAll("marker")
        .data(["end"])      // Different link/path types can be defined here
        .enter().append("svg:marker")    // This section adds in the arrows
        .attr("id", String)
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 31)
        .attr("refY", -1.5)
        .attr("markerWidth", 10)
        .attr("markerHeight", 10)
        .attr("orient", "auto")
        .append("svg:path")
//        .attr("d", "M10,-5L0,0L10,5");
      .attr("d", "M0,-5L10,0L0,5");


      var link = container.selectAll(".gLink")
        .data(bilinks)
        .enter().append("g")
        .attr("class", "gLink")
        .append("path")
        .attr("class", "link")
        .attr("marker-end", "url(#end)");


      var linkText = container.selectAll(".gLink")
        .data(bilinks)
        .append("text")
        .text(function (d) {
          return d[1].rssi + " dBm";
        })
        .style("fill", "#000444666").style("font-family", "Arial").style("font-size", 12);


      var node = container.selectAll(".node")
        .data(graph.nodes)
        .enter()
        .append("g")
        .on('mousedown', function() { d3.event.stopPropagation(); })
        .call(force.drag);


      node.append('circle')
        .attr('r', 30)
        .style('fill', '#8badc4')
        .style('stroke', '#3a72b2')
        .style('opacity', function(d){
          if(d.deviceType === "Coordinator"){
            return .5;
          }
          else{
            return 0;
          }
        })
        .attr('class', 'selectify')
        .attr('stroke-opacity', function(d){
          if(d.deviceType === "Coordinator"){
            return 1;
          }
          else{
            return 0;
          }
        });

      node.append("circle")
        .attr("class", "node")
        .attr("r", function (d) {
          return radius(d.deviceType);
        })
        .style("fill", function (d) {
          return color(d.laptime);
        });

      node.append("text")
        .text(function (d) {
          return letter(d.deviceType);
        })
        .attr("x", -6)
        .attr("y", 8)
        .style("fill", "#000444666").style("font-family", "Arial").style("font-size", 20);

//      node.append("text")
//        .text(function (d) {
//          return d.shortAddress;
//        })
//        .attr("x", 20)
//        .style("fill", "#000444666").style("font-family", "Arial").style("font-size", 12);

      node.on('click', function(d) { click(d,true, this); });

      force
        .nodes(nodes)
        .links(links);


      setTimeout(function() {
        force.start();
        var n = 100;
        for (var i = n * n; i > 0; --i) force.tick();
        force.stop();
      }, 10);

      force.on("tick", function () {
        link.attr("d", function(d) {
          var dx = d[2].x - d[0].x,
            dy = d[2].y - d[0].y,
            dr = Math.sqrt(dx * dx + dy * dy) * 2;
          return "M" +
            d[0].x + "," +
            d[0].y + "A" +
            dr + "," + dr + " 0 0,1 " +
            d[2].x + "," +
            d[2].y;
        });
        node.attr("transform", function (d) {
          return "translate(" + d.x + "," + d.y + ")";
        });
        linkText.
          attr("x", function (d) {
            if (d[2].x > d[0].x) {
              return (d[0].x + (d[2].x - d[0].x) / 2);
            }
            else {
              return (d[2].x + (d[0].x - d[2].x) / 2);
            }
          })
          .attr("y", function (d) {
            if (d[2].y > d[0].y) {
              return (d[0].y + (d[2].y - d[0].y) / 2);
            }
            else {
              return (d[2].y + (d[0].y - d[2].y) / 2);
            }
          }
        );
      });
    });

  }

  function zoomed() {
    container.attr("transform", "translate(" + d3.event.translate + ")scale(" + d3.event.scale + ")");
  }

  refreshData();

  $scope.addThing = function () {
    refreshData();
  };

}]);
