import api from './axios';

export default {
  getTaxRulesAdminList() {
    return api.get('/tax/rules/admin/list');
  },
  updateTaxRule(ruleId, payload) {
    return api.put(`/tax/rules/admin/${ruleId}`, payload);
  },
  seedTaxRulesYear(year) {
    return api.post(`/tax/rules/admin/seed/${year}`);
  },
  checkTaxRulesAdmin() {
    return api.get('/tax/rules/admin/me');
  },
};
