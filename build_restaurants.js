const fs = require('fs');

function slugify(str) {
  return str
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/đ/g, 'd').replace(/Đ/g, 'd')
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-');
}

const inputItems = [
  {name:'Quan Com Nieu Ben Tre',nameOrig:'Quán Cơm Niêu Bến Tre',specialty:'Cơm niêu, cá kho tộ',address:'Huyện Châu Thành, Bến Tre',price_range:'80.000 - 200.000',open_hours:'09:00 - 21:00',best_dish:'Cơm niêu cá kho tộ khóm',rating_note:'Cơm niêu thơm, cá kho đậm đà vị miền Tây đúng điệu',_type:'place',_category:'restaurant',_province:'Bến Tre',_area:'ben-tre'},
  {name:'Nha hang Cay Dua',nameOrig:'Nhà hàng Cây Dừa',specialty:'Đặc sản dừa, hải sản',address:'Đường 3 Tháng 2, TP. Bến Tre',price_range:'150.000 - 350.000',open_hours:'10:00 - 21:30',best_dish:'Gà nướng lá dừa, tôm hấp nước dừa',rating_note:'Chuyên khai thác nguyên liệu dừa vào ẩm thực, độc đáo và đặc trưng',_type:'place',_category:'restaurant',_province:'Bến Tre',_area:'ben-tre'},
  {name:'Quan Bun Ca Ro Dong',nameOrig:'Quán Bún Cá Rô Đồng',specialty:'Bún cá rô đồng',address:'Huyện Mỏ Cày, Bến Tre',price_range:'30.000 - 50.000',open_hours:'06:00 - 13:00',best_dish:'Bún cá rô đồng nước trong',rating_note:'Đặc sản nông thôn Bến Tre, cá rô đồng tươi, nước dùng trong thanh',_type:'place',_category:'restaurant',_province:'Bến Tre',_area:'ben-tre'},
  {name:'Nha hang Song Long',nameOrig:'Nhà hàng Song Long',specialty:'Lẩu mắm, cá tai tượng',address:'TP. Bến Tre',price_range:'180.000 - 450.000',open_hours:'10:30 - 22:00',best_dish:'Cá tai tượng chiên xù',rating_note:'Nhà hàng đông khách, phục vụ tốt, cá tai tượng chiên giòn nổi tiếng',_type:'place',_category:'restaurant',_province:'Bến Tre',_area:'ben-tre'},
  {name:'Quan Banh Canh Cua Ben Tre',nameOrig:'Quán Bánh Canh Cua Bến Tre',specialty:'Bánh canh cua',address:'Trung tâm TP. Bến Tre',price_range:'35.000 - 65.000',open_hours:'06:00 - 14:00',best_dish:'Bánh canh cua đồng',rating_note:'Bánh canh sợi to, nước dùng đậm vị cua, hàng bán sáng rất đắt khách',_type:'place',_category:'restaurant',_province:'Bến Tre',_area:'ben-tre'},
  {name:'Quan Che Dua Ben Tre',nameOrig:'Quán Chè Dừa Bến Tre',specialty:'Chè dừa, tráng miệng',address:'Chợ Bến Tre, TP. Bến Tre',price_range:'15.000 - 40.000',open_hours:'08:00 - 22:00',best_dish:'Chè dừa nướng, kẹo dừa handmade',rating_note:'Điểm dừng chân nổi tiếng của khách du lịch, chè dừa thơm ngon đặc trưng',_type:'place',_category:'restaurant',_province:'Bến Tre',_area:'ben-tre'},
  {name:'Nha hang Truc Xanh',nameOrig:'Nhà hàng Trúc Xanh',specialty:'Đặc sản Bến Tre, tiệc nhóm',address:'Huyện Giồng Trôm, Bến Tre',price_range:'150.000 - 400.000',open_hours:'10:00 - 21:00',best_dish:'Vịt nấu chao cuốn bánh tráng',rating_note:'Không gian vườn cây mát mẻ, món vịt chao được đánh giá cao',_type:'place',_category:'restaurant',_province:'Bến Tre',_area:'ben-tre'},
  {name:'Quan Com Ba Muoi',nameOrig:'Quán Cơm Bà Mười',specialty:'Cơm tấm, bún nước lèo Trà Vinh',address:'Đường Nguyễn Thị Minh Khai, TP. Trà Vinh',price_range:'30.000 - 60.000',open_hours:'06:00 - 14:00',best_dish:'Bún nước lèo Trà Vinh',rating_note:'Quán lâu đời, nước lèo đậm vị mắm bò hóc kiểu Khmer',_type:'place',_category:'restaurant',_province:'Trà Vinh',_area:'tra-vinh'},
  {name:'Quan Bun Nuoc Leo Di Sau',nameOrig:'Quán Bún Nước Lèo Dì Sáu',specialty:'Bún nước lèo đặc sản Khmer',address:'Đường Lê Lợi, TP. Trà Vinh',price_range:'25.000 - 50.000',open_hours:'05:30 - 12:00',best_dish:'Bún nước lèo cá lóc, tôm tươi',rating_note:'Nổi tiếng từ thập niên 1990, hương vị truyền thống Khmer Nam Bộ',_type:'place',_category:'restaurant',_province:'Trà Vinh',_area:'tra-vinh'},
  {name:'Nha Hang Huong Que',nameOrig:'Nhà Hàng Hương Quê',specialty:'Đặc sản miền Tây, cua biển Cồn Chim',address:'Số 1 Đường 30/4, TP. Trà Vinh',price_range:'150.000 - 400.000',open_hours:'10:00 - 22:00',best_dish:'Cua rang me, lẩu mắm miền Tây',rating_note:'Không gian rộng, phù hợp tiệc gia đình, nguyên liệu tươi từ Cồn Chim',_type:'place',_category:'restaurant',_province:'Trà Vinh',_area:'tra-vinh'},
  {name:'Quan Chao Ca Loc Ba Ba',nameOrig:'Quán Cháo Cá Lóc Bà Ba',specialty:'Cháo cá lóc đồng, cháo lòng',address:'Chợ Trà Vinh, đường Trần Phú, TP. Trà Vinh',price_range:'25.000 - 45.000',open_hours:'05:00 - 11:00',best_dish:'Cháo cá lóc đồng nấu gừng',rating_note:'Điểm ăn sáng quen thuộc của người dân địa phương, cá lóc đồng tự nhiên',_type:'place',_category:'restaurant',_province:'Trà Vinh',_area:'tra-vinh'},
  {name:'Quan Banh Canh Ben Co',nameOrig:'Quán Bánh Canh Bến Có',specialty:'Bánh canh cua, bánh canh cá lóc',address:'Bến Có, huyện Châu Thành, Trà Vinh',price_range:'30.000 - 55.000',open_hours:'06:00 - 14:00',best_dish:'Bánh canh cua Bến Có',rating_note:'Đặc sản nổi danh huyện Châu Thành, du khách từ TP.HCM thường ghé',_type:'place',_category:'restaurant',_province:'Trà Vinh',_area:'tra-vinh'},
  {name:'Quan Banh Xeo Muoi Xinh',nameOrig:'Quán Bánh Xèo Mười Xinh',specialty:'Bánh xèo miền Tây, gỏi cuốn',address:'Đường Ngô Quyền, TP. Trà Vinh',price_range:'40.000 - 80.000',open_hours:'10:00 - 20:00',best_dish:'Bánh xèo tôm thịt giòn rụm',rating_note:'Bánh xèo giòn đặc trưng miền Tây, ăn kèm rau sống và nước mắm chua ngọt',_type:'place',_category:'restaurant',_province:'Trà Vinh',_area:'tra-vinh'},
  {name:'Quan Hu Tieu Mi Tau Hu',nameOrig:'Quán Hủ Tiếu Mì Tàu Hũ',specialty:'Hủ tiếu Nam Vang, mì đặc biệt',address:'Chợ đêm Trà Vinh, TP. Trà Vinh',price_range:'30.000 - 55.000',open_hours:'17:00 - 23:00',best_dish:'Hủ tiếu khô tôm thịt',rating_note:'Điểm ẩm thực chợ đêm, đông khách vào buổi tối',_type:'place',_category:'restaurant',_province:'Trà Vinh',_area:'tra-vinh'},
  {name:'Quan Lau Mam Ut Trinh',nameOrig:'Quán Lẩu Mắm Út Trinh',specialty:'Lẩu mắm bông súng, cá đồng',address:'Đường Lê Thánh Tông, TP. Trà Vinh',price_range:'80.000 - 180.000',open_hours:'10:00 - 21:00',best_dish:'Lẩu mắm bông súng cá linh',rating_note:'Đậm chất miền Tây, mắm cá tự làm, rau đồng phong phú',_type:'place',_category:'restaurant',_province:'Trà Vinh',_area:'tra-vinh'},
  {name:'Quan Com Tam Suon Bi Ut Hoa',nameOrig:'Quán Cơm Tấm Sườn Bì Út Hoa',specialty:'Cơm tấm sườn nướng, bì chả',address:'Đường Phạm Thái Bường, TP. Trà Vinh',price_range:'35.000 - 65.000',open_hours:'06:00 - 14:00 và 17:00 - 21:00',best_dish:'Cơm tấm sườn bì chả nước mắm đặc chế',rating_note:'Sườn nướng than hoa thơm, đông khách buổi sáng và chiều tối',_type:'place',_category:'restaurant',_province:'Trà Vinh',_area:'tra-vinh'},
  {name:'Nha Hang Con Chim',nameOrig:'Nhà Hàng Cồn Chim',specialty:'Đặc sản cồn, hải sản, chim trời',address:'Cồn Chim, xã Phong Thạnh, huyện Cầu Kè, Trà Vinh',price_range:'150.000 - 500.000',open_hours:'09:00 - 20:00',best_dish:'Cá nướng trui, gà ta đồng nướng sả',rating_note:'Nằm trong khu sinh thái Cồn Chim, đặc sản cồn độc đáo, view sông đẹp',_type:'place',_category:'restaurant',_province:'Trà Vinh',_area:'tra-vinh'},
  {name:'Quan Che Khmer Ba Dong',nameOrig:'Quán Chè Khmer Ba Động',specialty:'Chè Khmer, bánh tét lá cẩm',address:'Thị trấn Trà Cú, huyện Trà Cú, Trà Vinh',price_range:'15.000 - 40.000',open_hours:'07:00 - 19:00',best_dish:'Chè chuối nước dừa, bánh tét lá cẩm nhân đậu xanh',rating_note:'Mang đậm bản sắc ẩm thực Khmer Nam Bộ, gần chùa Khmer nổi tiếng',_type:'place',_category:'restaurant',_province:'Trà Vinh',_area:'tra-vinh'},
  {name:'Quan Ca Kho To Nam Hen',nameOrig:'Quán Cá Kho Tộ Năm Hên',specialty:'Cá đồng kho tộ, cá lóc nướng trui',address:'Đường Nguyễn Đáng, TP. Trà Vinh',price_range:'50.000 - 120.000',open_hours:'10:00 - 21:00',best_dish:'Cá lóc nướng trui cuốn bánh tráng',rating_note:'Cá đồng tươi sống, kho tộ đậm đà kiểu Nam Bộ truyền thống',_type:'place',_category:'restaurant',_province:'Trà Vinh',_area:'tra-vinh'},
  {name:'Quan Bun Bo Hue Nhi Kieu',nameOrig:'Quán Bún Bò Huế Nhị Kiều',specialty:'Bún bò Huế, bún riêu cua',address:'Đường Lý Thường Kiệt, TP. Trà Vinh',price_range:'30.000 - 55.000',open_hours:'06:00 - 13:00',best_dish:'Bún bò giò heo chả cua',rating_note:'Nồi nước lèo hầm xương đậm vị, đông khách ăn sáng',_type:'place',_category:'restaurant',_province:'Trà Vinh',_area:'tra-vinh'}
];

const summaries = [
  'Quán cơm niêu tại Huyện Châu Thành, Bến Tre chuyên phục vụ cơm niêu và cá kho tộ đặc trưng miền Tây. Món nổi bật là cơm niêu cá kho tộ khóm với giá 80.000-200.000 đồng. Cơm niêu thơm dẻo, cá kho đậm đà vị miền Tây đúng điệu. Mở cửa từ 09:00 đến 21:00, phù hợp cả bữa trưa lẫn tối.',
  'Nhà hàng Cây Dừa nằm trên Đường 3 Tháng 2, TP. Bến Tre, chuyên khai thác nguyên liệu dừa vào ẩm thực tạo nên sự độc đáo và đặc trưng. Giá từ 150.000-350.000 đồng. Món nổi bật gà nướng lá dừa và tôm hấp nước dừa. Mở cửa 10:00-21:30, thích hợp cho nhóm muốn trải nghiệm ẩm thực dừa Bến Tre.',
  'Quán Bún Cá Rô Đồng tại Huyện Mỏ Cày, Bến Tre phục vụ đặc sản nông thôn với cá rô đồng tươi và nước dùng trong thanh. Giá bình dân 30.000-50.000 đồng. Món đặc trưng là bún cá rô đồng nước trong. Chỉ phục vụ buổi sáng từ 06:00 đến 13:00, lý tưởng cho bữa sáng địa phương.',
  'Nhà hàng Song Long tại TP. Bến Tre nổi tiếng với lẩu mắm và cá tai tượng chiên xù giòn rụm. Giá từ 180.000-450.000 đồng. Đông khách, phục vụ tốt, là lựa chọn cho các bữa ăn nhóm. Mở cửa 10:30-22:00, phù hợp bữa trưa và tối.',
  'Quán Bánh Canh Cua Bến Tre tại trung tâm TP. Bến Tre phục vụ bánh canh sợi to với nước dùng đậm vị cua đồng. Giá 35.000-65.000 đồng. Món đặc trưng bánh canh cua đồng. Mở cửa 06:00-14:00, hàng bán sáng rất đắt khách, nên đến sớm.',
  'Quán Chè Dừa Bến Tre ngay tại Chợ Bến Tre là điểm dừng chân nổi tiếng của khách du lịch. Chuyên chè dừa nướng và kẹo dừa handmade thơm ngon đặc trưng. Giá 15.000-40.000 đồng. Mở cửa dài từ 08:00-22:00, tiện ghé bất kỳ thời điểm nào trong ngày.',
  'Nhà hàng Trúc Xanh tại Huyện Giồng Trôm, Bến Tre có không gian vườn cây mát mẻ, thích hợp tiệc nhóm. Chuyên đặc sản Bến Tre với món vịt nấu chao cuốn bánh tráng được đánh giá cao. Giá 150.000-400.000 đồng. Mở cửa 10:00-21:00.',
  'Quán Cơm Bà Mười tại đường Nguyễn Thị Minh Khai, TP. Trà Vinh là quán lâu đời chuyên bún nước lèo Trà Vinh với nước lèo đậm vị mắm bò hóc kiểu Khmer. Giá bình dân 30.000-60.000 đồng. Phục vụ buổi sáng từ 06:00-14:00, phù hợp bữa sáng và trưa.',
  'Quán Bún Nước Lèo Dì Sáu trên đường Lê Lợi, TP. Trà Vinh nổi tiếng từ thập niên 1990 với hương vị truyền thống Khmer Nam Bộ. Món đặc sắc bún nước lèo cá lóc tôm tươi. Giá 25.000-50.000 đồng. Chỉ phục vụ buổi sáng sớm từ 05:30-12:00.',
  'Nhà Hàng Hương Quê tại Số 1 Đường 30/4, TP. Trà Vinh có không gian rộng phù hợp tiệc gia đình, sử dụng nguyên liệu tươi từ Cồn Chim. Chuyên đặc sản miền Tây với cua rang me và lẩu mắm miền Tây. Giá 150.000-400.000 đồng. Mở cửa 10:00-22:00.',
  'Quán Cháo Cá Lóc Bà Ba tại Chợ Trà Vinh là điểm ăn sáng quen thuộc của người dân địa phương. Chuyên cháo cá lóc đồng tự nhiên nấu gừng và cháo lòng. Giá 25.000-45.000 đồng. Phục vụ sáng sớm từ 05:00-11:00.',
  'Quán Bánh Canh Bến Có tại Bến Có, huyện Châu Thành là đặc sản nổi danh thu hút du khách từ TP.HCM. Chuyên bánh canh cua và bánh canh cá lóc Bến Có. Giá 30.000-55.000 đồng. Phục vụ buổi sáng từ 06:00-14:00.',
  'Quán Bánh Xèo Mười Xinh trên đường Ngô Quyền, TP. Trà Vinh nổi tiếng với bánh xèo giòn đặc trưng miền Tây, ăn kèm rau sống và nước mắm chua ngọt. Chuyên bánh xèo tôm thịt và gỏi cuốn. Giá 40.000-80.000 đồng. Mở cửa 10:00-20:00.',
  'Quán Hủ Tiếu Mì Tàu Hũ tại Chợ đêm Trà Vinh là điểm ẩm thực buổi tối đông khách, chuyên hủ tiếu Nam Vang và mì đặc biệt. Món nổi bật hủ tiếu khô tôm thịt. Giá 30.000-55.000 đồng. Chỉ phục vụ buổi tối từ 17:00-23:00.',
  'Quán Lẩu Mắm Út Trinh trên đường Lê Thánh Tông, TP. Trà Vinh đậm chất miền Tây với mắm cá tự làm và rau đồng phong phú. Món đặc sắc lẩu mắm bông súng cá linh. Giá 80.000-180.000 đồng. Mở cửa 10:00-21:00.',
  'Quán Cơm Tấm Sườn Bì Út Hoa trên đường Phạm Thái Bường, TP. Trà Vinh chuyên sườn nướng than hoa thơm, đông khách buổi sáng và chiều tối. Món đặc trưng cơm tấm sườn bì chả nước mắm đặc chế. Giá 35.000-65.000 đồng.',
  'Nhà Hàng Cồn Chim nằm trong khu sinh thái Cồn Chim, xã Phong Thạnh, huyện Cầu Kè với view sông đẹp. Chuyên đặc sản cồn độc đáo gồm cá nướng trui và gà ta đồng nướng sả. Giá 150.000-500.000 đồng. Mở cửa 09:00-20:00.',
  'Quán Chè Khmer Ba Động tại thị trấn Trà Cú, huyện Trà Cú mang đậm bản sắc ẩm thực Khmer Nam Bộ, gần chùa Khmer nổi tiếng. Chuyên chè chuối nước dừa và bánh tét lá cẩm nhân đậu xanh. Giá 15.000-40.000 đồng. Mở cửa 07:00-19:00.',
  'Quán Cá Kho Tộ Năm Hên trên đường Nguyễn Đáng, TP. Trà Vinh chuyên cá đồng tươi sống kho tộ đậm đà kiểu Nam Bộ truyền thống. Món nổi bật cá lóc nướng trui cuốn bánh tráng. Giá 50.000-120.000 đồng. Mở cửa 10:00-21:00.',
  'Quán Bún Bò Huế Nhị Kiều trên đường Lý Thường Kiệt, TP. Trà Vinh phục vụ nồi nước lèo hầm xương đậm vị, đông khách ăn sáng. Chuyên bún bò giò heo chả cua và bún riêu cua. Giá 30.000-55.000 đồng. Phục vụ buổi sáng từ 06:00-13:00.'
];

const raw = fs.readFileSync('C:/Code/vinhlong360/web/data.json');
const bom = raw[0]===0xEF && raw[1]===0xBB && raw[2]===0xBF;
const str = bom ? raw.slice(3).toString('utf8') : raw.toString('utf8');
const db = JSON.parse(str);

const existingIds = new Set(db.entities.map(function(e) { return e.id; }));
const existingNames = new Set(db.entities.map(function(e) { return e.name; }));

let addedCount = 0;
let skippedCount = 0;

inputItems.forEach(function(item, idx) {
  const area = item._area;
  const nameSlug = slugify(item.name);
  const id = nameSlug + '-' + area;

  if (existingIds.has(id) || existingNames.has(item.nameOrig)) {
    skippedCount++;
    return;
  }

  const entity = {
    id: id,
    type: item._type,
    name: item.nameOrig,
    placeId: null,
    summary: summaries[idx],
    source: 'curated',
    status: 'provisional',
    verified: false,
    confidence: 0.7,
    updatedAt: '2026-06-11T00:00:00Z',
    coords: null,
    attributes: {
      specialty: item.specialty,
      address: item.address,
      price_range: item.price_range,
      open_hours: item.open_hours,
      best_dish: item.best_dish,
      rating_note: item.rating_note,
      province_old: item._province,
      area: item._area,
      category: item._category
    }
  };

  db.entities.push(entity);
  existingIds.add(id);
  existingNames.add(item.nameOrig);
  addedCount++;
});

fs.writeFileSync('C:/Code/vinhlong360/web/data.json', JSON.stringify(db, null, 2), 'utf8');
console.log('Added: ' + addedCount);
console.log('Skipped: ' + skippedCount);
console.log('Total entities now: ' + db.entities.length);
