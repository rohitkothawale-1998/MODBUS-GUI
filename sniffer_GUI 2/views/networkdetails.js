mapApp.directive('networkDetails', function () {
  return {
    restrict: 'E',
    scope: {
      node: '='
    },
    templateUrl: 'views/networkdetails.tpl.html',
    link: function (scope, element) {
      scope.$on("NODE_CLICKED_EVENT", function (event, message) {
        scope.deviceType = message.deviceType;      
//        scope.deviceType = function () {
//          if (parseInt(message.deviceType) === 0) {
//            return "Coordinator";
//          }
//          else if (parseInt(message.deviceType) === 1) {
//            return "Router";
//          }
//          else if (parseInt(message.deviceType) === 2) {
//            return "End Device";
//          }
//          else if(parseInt(message.deviceType) === 3){
//            return "Disconnected";
//          }
//        }();

        if (scope.deviceType !== "Disconnected") {
          scope.address = message.ieee_address;
          scope.shortAddress = message.shortAddress;
          scope.memory = parseInt(message.workingMemory, 16);
          scope.memoryPercent = (parseInt(message.workingMemory, 16) / 3000) * 100;
          scope.uptime = parseInt(message.deviceUptime, 16);
          scope.packetLoss = message.packetLoss;
          scope.retries = message.txFailure;
          scope.hopcount = message.hopcount; 
          scope.laptime = message.laptime;  
          scope.channel = message.chan; 
          scope.sku = message.sku; 
          scope.firmware = message.fwvers;           
        }else{
          scope.address = "-";
          scope.shortAddress = "-";
          scope.memory = "-";
          scope.memoryPercent  = "-";
          scope.uptime = "-";
          scope.packetLoss = "-";
          scope.retries = "-";
          scope.hopcount = "-";  
          scope.laptime = "-";
          scope.channel = "-"; 
          scope.sku = "-";   
          scope.firmware = "-";          
        }

        scope.$apply();
      });
    }
  };
});